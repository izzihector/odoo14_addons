# -*- coding: utf-8 -*-
###############################################################################
#
#   Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#   Copyright (C) 2016-today Geminate Consultancy Services (<http://geminatecs.com>).
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import api, fields, models


class Website(models.Model):
    _inherit = 'website'

    captcha_sitekey = fields.Char()
    captcha_secretkey = fields.Char()
    login_page = fields.Boolean()
    sign_up = fields.Boolean()
    reset_password = fields.Boolean()


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    captcha_sitekey = fields.Char(
        string="Recaptcha Site Key",
        related='website_id.captcha_sitekey',
        readonly=False,
        required=True,
    )
    captcha_secretkey = fields.Char(
        string="Recaptcha Secret Key",
        related='website_id.captcha_secretkey',
        readonly=False,
        required=True,
    )

    login_page = fields.Boolean(
        string="Login",
        related='website_id.login_page',
        readonly=False,
    )

    sign_up = fields.Boolean(
        string="Signup",
        related='website_id.sign_up',
        readonly=False,
    )

    reset_password = fields.Boolean(
        string="Reset Password",
        related='website_id.reset_password',
        readonly=False,
    )