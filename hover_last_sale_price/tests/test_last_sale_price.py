# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install', 'hover_last_sale_price')
class TestLastSalePrice(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.company.write({
            'lsp_enabled': True,
            'lsp_hover_enabled': True,
            'lsp_hover_limit': 5,
            'lsp_suggest_enabled': True,
        })
        # 19.0: units of measure are always enabled (no uom.group_uom).
        cls.SaleLine = cls.env['sale.order.line']
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')

        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'LSP Company Currency',
            'currency_id': cls.company.currency_id.id,
            'company_id': cls.company.id,
        })
        partner_vals = {'property_product_pricelist': cls.pricelist.id}
        cls.customer = cls.env['res.partner'].create(
            dict(partner_vals, name='LSP Customer', is_company=True))
        cls.contact = cls.env['res.partner'].create(
            dict(partner_vals, name='LSP Buyer', parent_id=cls.customer.id,
                 type='contact'))
        cls.other_customer = cls.env['res.partner'].create(
            dict(partner_vals, name='LSP Other Customer', is_company=True))

        product_vals = {
            'type': 'consu',
            'list_price': 50.0,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'taxes_id': [(6, 0, [])],
        }
        cls.product = cls.env['product.product'].create(
            dict(product_vals, name='LSP Widget'))
        cls.product_b = cls.env['product.product'].create(
            dict(product_vals, name='LSP Gadget'))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @classmethod
    def _create_order(cls, price, days_ago=30, partner=None, product=None,
                      qty=1.0, uom=None, pricelist=None, discount=0.0,
                      confirm=True, company=None):
        vals = {
            'partner_id': (partner or cls.customer).id,
            'pricelist_id': (pricelist or cls.pricelist).id,
            'order_line': [(0, 0, {
                'product_id': (product or cls.product).id,
                'product_uom_qty': qty,
                'product_uom_id': (uom or cls.uom_unit).id,
                'price_unit': price,
                'discount': discount,
            })],
        }
        SaleOrder = cls.env['sale.order']
        if company:
            vals['company_id'] = company.id
            SaleOrder = SaleOrder.with_company(company)
        order = SaleOrder.create(vals)
        if confirm:
            order.action_confirm()
        # action_confirm() stamps date_order with now(): set the history date
        # afterwards so ordering by date can be asserted.
        order.date_order = fields.Datetime.now() - timedelta(days=days_ago)
        return order

    def _history(self, partner=None, product=None, order=None, **kwargs):
        return self.SaleLine.lsp_get_history(
            (product or self.product).id,
            (partner or self.customer).id,
            order_id=order.id if order else False,
            company_id=self.company.id,
            **kwargs)

    def _new_order_form(self, partner=None):
        order_form = Form(self.env['sale.order'])
        order_form.partner_id = partner or self.customer
        return order_form

    def _suggested_price(self, product=None, uom=None, partner=None):
        order_form = self._new_order_form(partner)
        with order_form.order_line.new() as line:
            line.product_id = product or self.product
            if uom:
                line.product_uom_id = uom
        order = order_form.save()
        return order.order_line.price_unit

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def test_01_settings_default_off(self):
        new_company = self.env['res.company'].create({'name': 'LSP Fresh Co'})
        self.assertFalse(new_company.lsp_enabled)
        self.assertFalse(new_company.lsp_hover_enabled)
        self.assertFalse(new_company.lsp_suggest_enabled)
        self.assertEqual(new_company.lsp_hover_limit, 5)

    def test_02_settings_round_trip(self):
        self.company.write({'lsp_enabled': False, 'lsp_hover_enabled': False,
                            'lsp_suggest_enabled': False})
        settings = self.env['res.config.settings'].create({
            'lsp_enabled': True,
            'lsp_hover_enabled': True,
            'lsp_hover_limit': 3,
            'lsp_suggest_enabled': False,
        })
        settings.execute()
        self.assertTrue(self.company.lsp_enabled)
        self.assertTrue(self.company._lsp_hover_active())
        self.assertFalse(self.company._lsp_suggest_active())
        self.assertEqual(self.company.lsp_hover_limit, 3)

    def test_03_sub_options_need_master_toggle(self):
        self.company.lsp_enabled = False
        self.assertTrue(self.company.lsp_hover_enabled)
        self.assertFalse(self.company._lsp_hover_active())
        self.assertFalse(self.company._lsp_suggest_active())

    def test_04_limit_constraint(self):
        for invalid in (0, -1, 51):
            with self.assertRaises(ValidationError):
                self.company.lsp_hover_limit = invalid
        self.company.lsp_hover_limit = 50
        self.assertEqual(self.company.lsp_hover_limit, 50)

    def test_05_order_hover_flag(self):
        order = self.env['sale.order'].create({'partner_id': self.customer.id})
        self.assertTrue(order.lsp_hover_enabled)
        self.company.lsp_hover_enabled = False
        order.invalidate_recordset(['lsp_hover_enabled'])
        self.assertFalse(order.lsp_hover_enabled)

    # ------------------------------------------------------------------
    # Historical price retrieval
    # ------------------------------------------------------------------
    def test_10_history_most_recent_first(self):
        # Created out of chronological order on purpose: ordering must follow
        # the order date, not the record id.
        self._create_order(30.0, days_ago=10)
        self._create_order(10.0, days_ago=90)
        self._create_order(20.0, days_ago=50)
        data = self._history()
        self.assertTrue(data['enabled'])
        self.assertEqual([l['price_unit'] for l in data['lines']],
                         [30.0, 20.0, 10.0])
        dates = [l['date_raw'] for l in data['lines']]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_11_history_limit_n(self):
        for i in range(7):
            self._create_order(100.0 + i, days_ago=70 - i * 10)
        data = self._history()
        self.assertEqual(data['limit'], 5)
        self.assertEqual(len(data['lines']), 5)
        self.assertEqual([l['price_unit'] for l in data['lines']],
                         [106.0, 105.0, 104.0, 103.0, 102.0])

        self.company.lsp_hover_limit = 2
        data = self._history()
        self.assertEqual(data['limit'], 2)
        self.assertEqual([l['price_unit'] for l in data['lines']],
                         [106.0, 105.0])

        self.company.lsp_hover_limit = 50
        self.assertEqual(len(self._history()['lines']), 7)

    def test_12_history_exclusions(self):
        self._create_order(40.0, days_ago=40)                     # kept
        self._create_order(99.0, days_ago=5, confirm=False)      # draft
        cancelled = self._create_order(88.0, days_ago=4)
        cancelled._action_cancel()                                # cancelled
        self._create_order(77.0, days_ago=3,
                           partner=self.other_customer)           # other customer
        self._create_order(66.0, days_ago=2, product=self.product_b)  # other product
        current = self._create_order(55.0, days_ago=1)            # current order
        data = self._history(order=current)
        self.assertEqual([l['price_unit'] for l in data['lines']], [40.0])
        # Without the exclusion the current order is the latest entry.
        self.assertEqual(self._history()['lines'][0]['price_unit'], 55.0)

    def test_13_history_whole_commercial_entity(self):
        self._create_order(45.0, days_ago=20, partner=self.contact)
        self._create_order(35.0, days_ago=40, partner=self.customer)
        expected = [45.0, 35.0]
        for partner in (self.customer, self.contact):
            data = self._history(partner=partner)
            self.assertEqual([l['price_unit'] for l in data['lines']], expected)
            self.assertEqual(data['partner_name'], self.customer.display_name)

    def test_14_history_company_isolation(self):
        other_company = self.env['res.company'].create({'name': 'LSP Other Co'})
        self.env.user.company_ids |= other_company
        other_pricelist = self.env['product.pricelist'].create({
            'name': 'LSP Other Co Pricelist',
            'currency_id': other_company.currency_id.id,
            'company_id': other_company.id,
        })
        self._create_order(11.0, days_ago=1, pricelist=other_pricelist,
                           company=other_company)
        self._create_order(22.0, days_ago=10)
        data = self._history()
        self.assertEqual([l['price_unit'] for l in data['lines']], [22.0])

    def test_15_history_disabled(self):
        self._create_order(30.0)
        self.company.lsp_hover_enabled = False
        data = self._history()
        self.assertFalse(data['enabled'])
        self.assertEqual(data['lines'], [])
        self.company.write({'lsp_hover_enabled': True, 'lsp_enabled': False})
        self.assertFalse(self._history()['enabled'])

    def test_16_history_payload(self):
        self._create_order(12.5, days_ago=15, qty=3.0, discount=10.0)
        data = self._history()
        self.assertEqual(data['product_name'], self.product.display_name)
        line = data['lines'][0]
        for key in ('id', 'order_id', 'order_name', 'date', 'date_raw', 'qty',
                    'qty_fmt', 'uom_id', 'uom_name', 'price_unit', 'price_fmt',
                    'currency_id', 'discount', 'discount_fmt',
                    'normalized_price', 'normalized_fmt'):
            self.assertIn(key, line)
        self.assertEqual(line['qty'], 3.0)
        self.assertEqual(line['uom_id'], self.uom_unit.id)
        self.assertEqual(line['discount'], 10.0)
        self.assertTrue(line['price_fmt'])
        # Same UoM and currency: no normalized hint displayed.
        self.assertFalse(line['normalized_fmt'])
        self.assertAlmostEqual(line['normalized_price'], 12.5)

    def test_18_history_includes_locked_orders(self):
        # Locking keeps the order in state 'sale' (no 'done' state).
        locked = self._create_order(61.0, days_ago=3)
        locked.action_lock()
        self.assertTrue(locked.locked)
        self.assertEqual(locked.state, 'sale')
        self._create_order(52.0, days_ago=30)
        data = self._history()
        self.assertEqual([l['price_unit'] for l in data['lines']], [61.0, 52.0])
        self.assertEqual(self._suggested_price(), 61.0)

    def test_17_history_empty_for_new_customer(self):
        self._create_order(30.0)
        data = self._history(partner=self.other_customer)
        self.assertTrue(data['enabled'])
        self.assertEqual(data['lines'], [])

    # ------------------------------------------------------------------
    # Price suggestion
    # ------------------------------------------------------------------
    def test_20_suggestion_applied(self):
        self._create_order(30.0, days_ago=60)
        self._create_order(42.0, days_ago=5)
        self.assertEqual(self._suggested_price(), 42.0)

    def test_21_suggestion_from_contact_history(self):
        self._create_order(37.0, days_ago=5, partner=self.contact)
        self.assertEqual(self._suggested_price(partner=self.customer), 37.0)

    def test_22_suggestion_disabled_uses_pricelist(self):
        self._create_order(42.0)
        self.company.lsp_suggest_enabled = False
        self.assertEqual(self._suggested_price(), 50.0)
        self.company.write({'lsp_suggest_enabled': True, 'lsp_enabled': False})
        self.assertEqual(self._suggested_price(), 50.0)

    def test_23_suggestion_without_history_uses_pricelist(self):
        self._create_order(42.0, partner=self.other_customer)
        self.assertEqual(self._suggested_price(), 50.0)

    def test_24_suggestion_independent_of_hover(self):
        self._create_order(42.0)
        self.company.lsp_hover_enabled = False
        self.assertEqual(self._suggested_price(), 42.0)

    def test_25_suggestion_uom_normalization(self):
        # Last sold: 2 dozens at 120 / dozen  ->  10 / unit.
        self._create_order(120.0, qty=2.0, uom=self.uom_dozen)
        self.assertAlmostEqual(self._suggested_price(), 10.0, places=2)
        self.assertAlmostEqual(
            self._suggested_price(uom=self.uom_dozen), 120.0, places=2)
        # The hover shows the original price plus the normalized hint.
        line = self._history(uom_id=self.uom_unit.id)['lines'][0]
        self.assertEqual(line['uom_id'], self.uom_dozen.id)
        self.assertEqual(line['price_unit'], 120.0)
        self.assertAlmostEqual(line['normalized_price'], 10.0, places=2)
        self.assertTrue(line['normalized_fmt'])

    def test_26_suggestion_incompatible_uom_ignored(self):
        history_line = self._create_order(120.0, uom=self.uom_dozen).order_line
        self.assertIsNone(history_line._lsp_normalized_price(target_uom=self.uom_kg))

    def test_27_suggestion_currency_normalization(self):
        company_currency = self.company.currency_id
        foreign = self.env.ref('base.EUR')
        if foreign == company_currency:
            foreign = self.env.ref('base.USD')
        foreign.active = True
        today = fields.Date.context_today(self.SaleLine)
        Rate = self.env['res.currency.rate']
        Rate.search([('currency_id', 'in', (foreign | company_currency).ids),
                     ('company_id', 'in', (False, self.company.id)),
                     ('name', '=', today)]).unlink()
        Rate.create([
            {'name': today, 'rate': 1.0, 'currency_id': company_currency.id,
             'company_id': self.company.id},
            {'name': today, 'rate': 2.0, 'currency_id': foreign.id,
             'company_id': self.company.id},
        ])
        foreign_pricelist = self.env['product.pricelist'].create({
            'name': 'LSP Foreign', 'currency_id': foreign.id,
            'company_id': self.company.id,
        })
        order = self._create_order(200.0, days_ago=0, pricelist=foreign_pricelist)
        self.assertEqual(order.currency_id, foreign)
        # 200 foreign at 2.0 per company-currency unit -> 100 company currency.
        self.assertAlmostEqual(self._suggested_price(), 100.0, places=2)
        line = self._history(currency_id=company_currency.id)['lines'][0]
        self.assertEqual(line['currency_id'], foreign.id)
        self.assertAlmostEqual(line['normalized_price'], 100.0, places=2)
        self.assertTrue(line['normalized_fmt'])

    def test_28_suggestion_on_create_and_explicit_price_kept(self):
        self._create_order(42.0)
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {'product_id': self.product.id}),
                (0, 0, {'product_id': self.product.id, 'price_unit': 7.0}),
            ],
        })
        self.assertEqual(order.order_line.mapped('price_unit'), [42.0, 7.0])

    def test_29_suggestion_kept_on_quantity_change(self):
        self._create_order(42.0)
        order_form = self._new_order_form()
        with order_form.order_line.new() as line:
            line.product_id = self.product
            line.product_uom_qty = 12.0
        order = order_form.save()
        self.assertEqual(order.order_line.price_unit, 42.0)

    def test_30_suggestion_skip_context(self):
        self._create_order(42.0)
        order = self.env['sale.order'].with_context(lsp_skip_suggestion=True).create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {'product_id': self.product.id})],
        })
        self.assertEqual(order.order_line.price_unit, 50.0)

    def test_32_manual_price_kept_on_quantity_change(self):
        # 18.0 technical_price_unit contract: a price typed by the user must
        # survive later quantity changes, a suggested one is re-applied.
        self._create_order(42.0)
        order_form = self._new_order_form()
        with order_form.order_line.new() as line:
            line.product_id = self.product
            self.assertEqual(line.price_unit, 42.0)
            line.price_unit = 99.0
            line.product_uom_qty = 5.0
            self.assertEqual(line.price_unit, 99.0)
        order = order_form.save()
        self.assertEqual(order.order_line.price_unit, 99.0)

    def test_31_suggestion_skips_section_lines(self):
        self._create_order(42.0)
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {'display_type': 'line_section',
                                   'name': 'Section'})],
        })
        self.assertEqual(order.order_line.price_unit, 0.0)
