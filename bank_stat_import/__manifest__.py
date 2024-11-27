# -*- coding: utf-8 -*-
# __manifest__.py
{
    'name': "Bank Statement Import",
    'summary': "Импорт банковских выписок",
    'description': """  Импорт банковских выписок """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '17.0.0.2',
    'depends': ['base', 'account', 'crm',  ],
    # "assets": {
    #     "web.assets_backend": [
    #         "common_tools/static/src/**/*",
    #     ],
    # },

    'data': [
        'views/bank_statement_import_wizard.xml',
        'security/ir.model.access.csv',
        'views/menu_action_view.xml',
       # 'data/data.xml',
    ],

    'demo': [

    ],
    'sequence': 1,
    'installable': True,
    'application': True,
    'license': 'LGPL-3',

}
