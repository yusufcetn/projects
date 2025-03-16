{
    'name': 'Custom Signup Page',
    'version': '17.0.1.1.1',
    'summary': 'Adds custom fields to the signup page',
    'description': """
        This module adds birth date, birth place, and gender fields to the Odoo signup page.
    """,
    'author': 'Yusuf Çetin',
    'category': 'Tools',
    'depends': ['base', 'auth_signup', 'education_base'],
    'license' : 'LGPL-3',
    'data': [
        'data/sequence.xml',
        'data/age_category_cron.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/views.xml',
        'views/res_partner_view_inherited.xml',
        'views/res_partner_pages_view.xml',
        'views/res_partner_tree_view_inherited.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
