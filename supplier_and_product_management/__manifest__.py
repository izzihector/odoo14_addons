{
    'name': 'Supplier and Product management',
    'summary': 'Supplier and Product management',
    'description': '''
        Management create supplier and product 
    ''',
    'category': 'SCGL',
    'version': '14.0.1.1',
    'author': 'SCGLEGACY(THAILAND) CO.,LTD(HEAD OFFICE)',
    'website': 'https://scgl.co.th/',
    "depends": ["base", "web", "stock", "product"],
    'data': [
            'data/sequence.xml',
            'security/ir.model.access.csv',
            'views/supplier_views.xml',
             ],
    'demo': [],
}
