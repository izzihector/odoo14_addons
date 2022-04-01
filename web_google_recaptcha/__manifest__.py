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
{
    'name': 'Google reCAPTCHA',
    'summary': 'Geminate comes with a feature to add google reCAPTCHA on Login page, Signup Page and Reset Password Page.',
    'author': 'Geminate Consultancy Services',
    'license': 'Other proprietary',
    'website': 'https://www.geminatecs.com/',
    'version': '1.0.0',
    # version 14.0.1.0.0
    "category": "Website",
    'depends': ['website', 'auth_signup'],
    "description": """
       Geminate comes with a feature to add google reCAPTCHA on Login page, Signup Page and Reset Password Page. 
       by using this feature, google reCAPTCHA protects your website from fraud and abuse. CAPTCHA stands for Completely
       Automated Public Turing Test to Tell Computers and Humans Apart. main goal of this app is to check if a user is a real
       person or a bot. it is easy for humans to solve, but hard for bots and other malicious software to figure out.
    """,

    "data": [
        'views/website_config_settings.xml',
        'views/login_templates.xml',
    ],

    'images': ['static/description/banner.png'],
    'qweb' : [],
    'installable': True,
    'auto_install': False,
    'price': 9.99,
    'currency': 'EUR'
}
