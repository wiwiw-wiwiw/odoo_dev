# -*- coding: utf-8 -*-
{
    'name': "Bank Statement Parser",
    # имя модуля

    'summary': "Импорт банковских выписок",
    # краткое описание

    'description': """  Импорт банковских выписок """,
    # длинное описание

    'author': "My Company",
    # автор

    'website': "https://www.yourcompany.com",
    # вебсайт

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    # категория модуля

    'version': '17.0.0.1',
    # версия модуля 17 - для odoo17

    # any module necessary for this one to work correctly
    'depends': ['base', 'account',  ],
    # зависимости модуля от других модулей

   # "assets": {
   #     "web.assets_backend": [
    #        "common_tools/static/src/**/*",
    #    ],
   # },

    # always loaded
    
    'data': [ 
        'views/views.xml',
       
        'security/ir.model.access.csv', 
    ],
    #    'views/templates.xml',


    # only loaded in demonstration mode
    'demo': [ 

    ],
    #    'demo/demo.xml',
    # демонстрационные данные модуля

    'sequence': 1,
    # приоритет отображения в магазине приложений odoo

    'installable': True,
    # устанавливаемый ли модуль

    'application': True,
    # это приложение?

    #'post_init_hook': 'account_past_init',
    # действия после установки модуля

    #'assets': {   },
    # 

    'license': 'LGPL-3',
    # лицензия

    #'pre_init_hook':"",
    # действия перед установкой модуля

    #'uninstall_hook':"",
    # действия после удаления модуля

    #'auto_install':"True",
    #


    #'maintainer':"",
    # сопровождающий модуля?

    #'external_dependencies':"",
    # зависимость от библиотек python как внешняя зависимость
    # при установке проверится есть ли данная библиотека и если ее нет, то odoo выдаст предупреждение


}

