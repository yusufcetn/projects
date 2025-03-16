# -*- coding: utf-8 -*-
{
    'name': 'Education',
    'version': '17.0.1.1.1',
    'summary': 'Education Base Module',
    'description': """
        This module provides custom functionality for Odoo 17.
    """,
    'author': 'Yusuf Çetin',
    'category': 'Contacts',
    'depends': [
        'contacts',
        'base',
        'website_sale',
    ],
    'license' : 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/action_types_view.xml',
        'views/menuitems.xml',
        'views/res_config_settigs_view_inherit.xml',
        'views/res_partner_sale_pricelist_checkbox.xml',
        'views/age_category_views.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence' : 1,
}

