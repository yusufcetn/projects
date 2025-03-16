# -*- coding: utf-8 -*-
{
    'name': "Custom Stripe Fee",

    'description': """
Adds transaction fee to Stripe payments
""",

    'author': "Yusuf Çetin",

    'category': 'Payment',
    'version': '17.0',
    'license' : 'LGPL-3',

    'depends': ['payment', 'website_sale'],

    'data': [
        'data/product_fee_data.xml',
        'views/payment_provider_fee_view.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_stripe_fee/static/src/js/compute_fee.js',
        ],
    },
    'installable' : True,
}

