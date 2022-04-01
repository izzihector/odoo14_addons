# -*- coding: utf-8 -*-
{
    'name': 'report invoicing',
    'version': '12.1.1.0',
    'category': 'Report Designer',
    'author': 'Afan',
    'website': 'https://afan.co.th',
    'description': u"""
Export report using Report Designer
""",
    'depends': [
        'account', 'sale'
    ],
    'data': [
        'report/paperformat.xml',
        'report/inv_report_action.xml',
        'report/inv_header.xml',
        'report/inv_template.xml',
    ],
    'application': False
    # 'report/header_footer.xml',

}
