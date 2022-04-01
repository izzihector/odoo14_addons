{
    'name': 'div_search_template',
    'summary': 'div report thai',
    'category': 'Accounting/Accounting',
    'version': '14.1.0.0',
    'description': """
Accounting Reports
==================
    """,
    'depends': ['account_accountant','account_reports', 'base','Balance_Sheet_thai'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_report_view.xml',
        'views/search_template_view.xml',
        'views/div_view.xml',
        'views/assets.xml',
    ],
    'qweb': [

    ],
    'auto_install': True,
    'installable': True,
}
