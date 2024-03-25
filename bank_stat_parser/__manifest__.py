# -*- coding: utf-8 -*-
{
    'name': "Bank Statement Parser",
    'summary': "Импорт банковских выписок",
    'description': """  Импорт банковских выписок """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base', 'account', 'web', 'common_tools' ],
    'data': [ 
        'views/bank_stat_parser_view.xml',
        
       
        'security/ir.model.access.csv', 
        'views/assets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            "bank_stat_parser/static/src/**/*",
            'bank_stat_parser/static/src/js/bank_stat_parser.js',
        
            # Другие файлы, которые нужно включить
        ],
    },
    'demo': [],
    'sequence': 1,
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

