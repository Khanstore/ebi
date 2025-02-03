# -*- coding: utf-8 -*-



{
    'name': "Eagle Data Import 2025",

    'summary': """
        Project to Upgrade database and export and import data between databases with xmlrpc, """,

    'description': """
        upgrade database to odoo versions and import data 
    """,

    'author': "SM Ashraf",
    'website': "https://www.khan-store.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sale',
    'version': '16.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'views/import_views.xml',
        'views/ebi.xml',
        'views/actions.xml',
        'views/menu.xml',


    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
}
