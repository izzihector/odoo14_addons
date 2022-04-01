{
    'name': 'report invoice',
    'version': '12.1.1.0',
    'category': 'Report Designer',
    'author': 'SCG LEGACY(THAILAND) CO.,LTD(HEAD OFFICE)',
    'website': 'https://scgl.co.th',
    'description': u"""
Export report using Report Designer
""",
    'depends': [
        'account'
    ],
    'data': [
        'report/paperformat.xml',
        'report/action_report.xml',
        'report/inv_temp.xml',
        'report/inv_header.xml'],
    'application': False

}
