{
    'name': 'thai tax report',
    'summary': 'print tax report',
    'category': 'Accounting/Accounting',
    'version': '1.0.0',
    'description': """
Accounting Reports
==================
    """,
    'depends': ['account_accountant', 'account_reports', 'base', 'l10n_th_tax_report'],
    'data': [
        "data/paper_format.xml",
        "data/report_data.xml",
        "views/tax_report.xml",

    ],
    'qweb': [

    ],
    'auto_install': True,
    'installable': True,
}
