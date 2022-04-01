{
    'name': 'journal_entries_report',
    'summary': 'journal_entries_report',
    'category': 'Accounting/Accounting',
    'version': '1.0.0',
    'description': """
Accounting Reports
==================
    """,
    'depends': ['account_accountant', 'account_reports', 'base'],
    'data': [
        "views/report_journal_entries_inv.xml",


    ],
    'qweb': [

    ],
    'auto_install': True,
    'installable': True,
}
