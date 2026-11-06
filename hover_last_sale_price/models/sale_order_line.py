# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare
from odoo.tools.misc import format_date, formatLang
from odoo.tools.sql import column_exists, create_index

_logger = logging.getLogger(__name__)

# Order line states that count as a real sale. In 17.0 the 'done' state is
# gone: locked orders stay in 'sale' with sale.order.locked = True.
LSP_SALE_STATES = ('sale',)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # ------------------------------------------------------------------
    # Performance: composite index serving the history lookup
    # ------------------------------------------------------------------
    def init(self):
        super().init()
        cr = self.env.cr
        needed = ('product_id', 'order_partner_id', 'company_id', 'state')
        if all(column_exists(cr, self._table, col) for col in needed):
            create_index(cr, 'sale_order_line_lsp_history_index',
                         self._table, list(needed))

    # ------------------------------------------------------------------
    # History retrieval
    # ------------------------------------------------------------------
    @api.model
    def _lsp_history_domain(self, partner, product, company,
                            exclude_order_ids=None):
        """Confirmed lines of ``product`` sold to the commercial entity of
        ``partner`` (company + all its contacts) in ``company``."""
        domain = [
            ('state', 'in', LSP_SALE_STATES),
            ('order_partner_id', 'child_of',
             partner.commercial_partner_id.id),
            ('product_id', '=', product.id),
            ('company_id', '=', company.id),
            ('display_type', '=', False),
            ('product_uom_qty', '>', 0),
        ]
        exclude_order_ids = [oid for oid in (exclude_order_ids or []) if oid]
        if exclude_order_ids:
            domain.append(('order_id', 'not in', exclude_order_ids))
        return domain

    @api.model
    def _lsp_find_history(self, partner, product, company, limit,
                          exclude_order_ids=None):
        """Return up to ``limit`` historical lines, most recent first.

        Ordering on ``order_id`` delegates to ``sale.order._order``
        (``date_order desc, id desc``) inside a single SQL query, so the
        database applies ORDER BY + LIMIT on the composite index.
        History is a business reference shared by the sales team, hence the
        sudo(); callers are responsible for checking access to the partner,
        the product and the company.
        """
        if not (partner and product and company) or limit <= 0:
            return self.browse()
        domain = self._lsp_history_domain(
            partner, product, company, exclude_order_ids)
        return self.sudo().with_context(active_test=False).search(
            domain, order='order_id, id desc', limit=limit)

    # ------------------------------------------------------------------
    # Normalization (UoM + currency)
    # ------------------------------------------------------------------
    def _lsp_normalized_price(self, target_uom=None, target_currency=None,
                              date=None):
        """Express this line's unit price in ``target_uom`` and
        ``target_currency``. Returns ``None`` when UoMs are not comparable."""
        self.ensure_one()
        price = self.price_unit
        src_uom = self.product_uom
        if target_uom and src_uom and target_uom != src_uom:
            if src_uom.category_id != target_uom.category_id:
                return None
            price = src_uom._compute_price(price, target_uom)
        src_currency = self.currency_id or self.order_id.currency_id
        if target_currency and src_currency and target_currency != src_currency:
            price = src_currency._convert(
                price, target_currency, self.company_id,
                date or fields.Date.context_today(self), round=False)
        return price

    # ------------------------------------------------------------------
    # Pricing engine: last sale price suggestion
    # ------------------------------------------------------------------
    # No @api.depends here on purpose: the override inherits the standard
    # triggers (product, UoM, quantity). Adding the customer as a trigger
    # would silently reprice every line when the customer is changed.
    def _compute_price_unit(self):
        """In v16 ``price_unit`` is a computed field: its compute is what the
        web client's onchange runs when product, UoM or quantity change, and
        what ``create()`` runs when no price is given. Hooking here (instead
        of a bare ``@api.onchange``) guarantees the suggestion survives the
        compute cascade (product -> UoM -> price) and also applies to lines
        created through the API or imports."""
        super()._compute_price_unit()
        if self.env.context.get('lsp_skip_suggestion'):
            return
        memo = {}
        for line in self:
            if (line.display_type or not line.product_id
                    or not line.product_uom or line.qty_invoiced > 0
                    or line.is_expense):
                continue
            order = line.order_id
            company = line.company_id or order.company_id
            partner = order.partner_id
            if not partner or not company or not company._lsp_suggest_active():
                continue
            exclude = tuple(order._origin.ids)
            key = (partner.commercial_partner_id.id, line.product_id.id,
                   company.id, exclude)
            if key not in memo:
                memo[key] = self._lsp_find_history(
                    partner, line.product_id, company, 1, exclude)
            history = memo[key]
            if not history:
                continue
            date = (order.date_order.date() if order.date_order
                    else fields.Date.context_today(line))
            price = history._lsp_normalized_price(
                line.product_uom,
                order.currency_id or company.currency_id,
                date)
            if price is not None:
                line.price_unit = price

    # ------------------------------------------------------------------
    # RPC endpoint for the hover widget
    # ------------------------------------------------------------------
    @api.model
    def lsp_get_history(self, product_id, partner_id, order_id=False,
                        company_id=False, uom_id=False, currency_id=False):
        """Payload consumed by the OWL hover popup. Values are formatted
        server-side in the user's language (dates, quantities, amounts)."""
        company = (self.env['res.company'].browse(company_id).exists()
                   if company_id else self.env.company)
        result = {'enabled': False, 'limit': 0, 'lines': [],
                  'product_name': '', 'partner_name': ''}
        if (not company or company not in self.env.user.company_ids
                or not company._lsp_hover_active()):
            return result
        result.update(enabled=True, limit=company.lsp_hover_limit)

        partner = self.env['res.partner'].browse(partner_id).exists()
        product = self.env['product.product'].browse(product_id).exists()
        if not partner or not product:
            return result
        # The user must be allowed to see the customer and the product.
        for record in (partner, product):
            record.check_access_rights('read')
            record.check_access_rule('read')

        target_uom = (self.env['uom.uom'].browse(uom_id).exists()
                      if uom_id else product.uom_id)
        target_currency = (self.env['res.currency'].browse(currency_id).exists()
                           if currency_id else company.currency_id)
        today = fields.Date.context_today(self)
        price_digits = self.env['decimal.precision'].precision_get(
            'Product Price')

        history = self._lsp_find_history(
            partner, product, company, company.lsp_hover_limit,
            [order_id] if order_id else None)
        lines = []
        for line in history:
            order = line.order_id
            currency = line.currency_id or order.currency_id
            local_date = fields.Datetime.context_timestamp(
                self, order.date_order).date()
            normalized = line._lsp_normalized_price(
                target_uom, target_currency, today)
            show_normalized = (
                normalized is not None
                and (line.product_uom != target_uom
                     or currency != target_currency)
                and float_compare(normalized, line.price_unit,
                                  precision_digits=price_digits) != 0
            )
            lines.append({
                'id': line.id,
                'order_id': order.id,
                'order_name': order.name,
                'date': format_date(self.env, local_date),
                'date_raw': fields.Date.to_string(local_date),
                'qty': line.product_uom_qty,
                'qty_fmt': formatLang(self.env, line.product_uom_qty,
                                      dp='Product Unit of Measure'),
                'uom_id': line.product_uom.id,
                'uom_name': line.product_uom.name,
                'price_unit': line.price_unit,
                'price_fmt': formatLang(self.env, line.price_unit,
                                        dp='Product Price',
                                        currency_obj=currency),
                'currency_id': currency.id,
                'discount': line.discount,
                'discount_fmt': (formatLang(self.env, line.discount,
                                            dp='Discount')
                                 if line.discount else ''),
                'normalized_price': normalized,
                'normalized_fmt': (formatLang(self.env, normalized,
                                              dp='Product Price',
                                              currency_obj=target_currency)
                                   if show_normalized else ''),
            })
        result.update(
            lines=lines,
            product_name=product.display_name,
            partner_name=partner.commercial_partner_id.display_name,
        )
        return result
