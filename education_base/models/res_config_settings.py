from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    assignment_user_id = fields.Many2one(
        'res.users',
        string='Assignment User',
        config_parameter='education_base.assignment_user_id'
    )

