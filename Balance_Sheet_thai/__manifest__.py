{
    'name' : 'Balance_Sheet_thai',
    'summary': 'print report thai',
    'category': 'Accounting/Accounting',
    'version': '1.0.0',
    'description': """
Accounting Reports
==================
    """,
    'depends': ['account_accountant','account_reports', 'base'],
    'data': [
        "views/report_financial.xml",

        'data/report_data.xml',
    ],
    'qweb': [

    ],
    'auto_install': True,
    'installable': True,
}
