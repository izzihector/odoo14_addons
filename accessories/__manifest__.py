# -*- coding: utf-8 -*-
{
    'name': 'accessories',
    'version': '14.0.0.0',
    'category': 'accessories',
    'author': 'SCG LEGACY(THAILAND) CO.,LTD(HEAD OFFICE)',
    'website': 'https://scgl.co.th',
    'description': u"""
Export report using Report Designer
""",
    'css': 'style/css/name_of_css_file.css',
    'depends': [
        'account', 'sale', 'product', 'mail',
    ],
    'data': [
        'view/view_mail.xml',
        'view/view_multiple_tax.xml',
        'view/view_product_scroll_bar.xml',

    ],
    'application': False
    # 'report/header_footer.xml',

}
