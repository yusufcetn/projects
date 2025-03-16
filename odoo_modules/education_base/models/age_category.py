from odoo import models, fields

class AgeCategory(models.Model):
    _name = 'age.category'
    _description = 'Age Category'

    name = fields.Char(string="Age Category")
    min_date = fields.Date(string="Minimum Birth Date")
    max_date = fields.Date(string="Maximum Birth Date")
