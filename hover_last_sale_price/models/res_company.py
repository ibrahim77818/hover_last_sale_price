# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

LSP_DEFAULT_LIMIT = 5
LSP_MAX_LIMIT = 50


class ResCompany(models.Model):
    _inherit = 'res.company'

    lsp_enabled = fields.Boolean(
        string='Last Sale Price',
        default=False,
        help="Track the prices previously charged to each customer and reuse "
             "them on sales order lines.",
    )
    lsp_hover_enabled = fields.Boolean(
        string='Show Price History on Hover',
        default=False,
        help="Display a popup with the customer's previous prices when "
             "hovering over the product of a sales order line.",
    )
    lsp_hover_limit = fields.Integer(
        string='Transactions to Show',
        default=LSP_DEFAULT_LIMIT,
        help="Number of previous confirmed sales displayed in the hover "
             "popup (1 to 50).",
    )
    lsp_suggest_enabled = fields.Boolean(
        string='Suggest Last Sale Price',
        default=False,
        help="Automatically fill the unit price of a new sales order line "
             "with the price last charged to the customer for that product.",
    )

    @api.constrains('lsp_hover_limit')
    def _check_lsp_hover_limit(self):
        for company in self:
            if not 1 <= company.lsp_hover_limit <= LSP_MAX_LIMIT:
                raise ValidationError(_(
                    "The number of transactions to show on hover must be "
                    "between 1 and %(max)s.") % {'max': LSP_MAX_LIMIT})

    def _lsp_hover_active(self):
        """Hover popup is effective only when the master toggle is on."""
        self.ensure_one()
        return bool(self.lsp_enabled and self.lsp_hover_enabled)

    def _lsp_suggest_active(self):
        """Price suggestion is effective only when the master toggle is on."""
        self.ensure_one()
        return bool(self.lsp_enabled and self.lsp_suggest_enabled)
