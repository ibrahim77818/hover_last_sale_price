# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lsp_enabled = fields.Boolean(
        related='company_id.lsp_enabled', readonly=False)
    lsp_hover_enabled = fields.Boolean(
        related='company_id.lsp_hover_enabled', readonly=False)
    lsp_hover_limit = fields.Integer(
        related='company_id.lsp_hover_limit', readonly=False)
    lsp_suggest_enabled = fields.Boolean(
        related='company_id.lsp_suggest_enabled', readonly=False)
