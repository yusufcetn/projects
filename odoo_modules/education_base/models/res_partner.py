from datetime import date, datetime

from odoo import models, fields,api
from odoo.http import request


class Partner(models.Model):
    _description = "Contact"
    _inherit = 'res.partner'

    partner_type = fields.Selection([('partner','Partner'),
                                           ('subpartner','Sub Partner'),
                                           ('school','School'),
                                           ('teacher','Teacher'),
                                           ('student','Student'),
                                           ('parent','Parent')],
                                          string='User Role')
    is_assign = fields.Boolean(default=False, string='Contacts to assign', track_visibility='onchange')
    
    nationality = fields.Many2one('res.country', string="Nationality")
    passport_number = fields.Char('Passport Number')
    identity_vat_number = fields.Char('Identity/VAT Number')

    special_pricelist_id = fields.Boolean('Special Pricelist')
