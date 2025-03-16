# -*- coding: utf-8 -*-
{
    "name": "Contact Manager In Website Portal",
    "summary": "Allows logged in portal users to manage their contacts",
    "author": "Yusuf Çetin",
    "category": "Portal",
    "version": "17.0",
    "depends": ["portal", "website", "website_slides", "signup_page", 'website_event'],
    "data": [
        "security/ir.model.access.csv",
        "security/ir.rule.csv",
        "views/contact_portal_template.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}