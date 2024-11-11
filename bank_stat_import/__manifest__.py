# -*- coding: utf-8 -*-
{
    'name': "Bank Statement Import",
    'summary': "Импорт банковских выписок",
    'description': """  Импорт банковских выписок """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '17.0.0.1',
    'depends': ['base', 'account', 'crm', 'common_tools', ],
    # "assets": {
    #     "web.assets_backend": [
    #         "common_tools/static/src/**/*",
    #     ],
    # },

    'data': [
        'views/bank_stat_import.xml',
        'security/ir.model.access.csv',
       # 'data/data.xml',
    ],

    'demo': [

    ],
    'sequence': 1,
    'installable': True,
    'application': True,
    'license': 'LGPL-3',

}
