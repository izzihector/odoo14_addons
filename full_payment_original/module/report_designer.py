# -*- coding: utf-8 -*-

from odoo import models, fields, api


class View(models.Model):
    _inherit = 'ir.ui.view'

    is_report_designer_template = fields.Boolean(string='Is Report Designer Template', default=False)

            