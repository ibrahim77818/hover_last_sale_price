# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    lsp_hover_enabled = fields.Boolean(
        string='Last Sale Price Hover',
        compute='_compute_lsp_hover_enabled',
        help="Technical flag read by the order line widget to decide whether "
             "the last sale price popup is available.",
    )

    @api.depends('company_id')
    def _compute_lsp_hover_enabled(self):
        for order in self:
            company = order.company_id or self.env.company
            order.lsp_hover_enabled = company._lsp_hover_active()
