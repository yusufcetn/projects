from odoo import models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):

        user = super(ResUsers, self).create(vals)

        if 'partner_id' in vals:
            partner = self.env['res.partner'].browse(vals['partner_id'])
            if partner.partner_type:
                if partner.partner_type == 'partner':
                    partner_group = self.env.ref('signup_page.group_partner_user')
                    user.groups_id = [(4, partner_group.id)]
                elif partner.partner_type == 'school':
                    school_group = self.env.ref('signup_page.group_school_user')
                    user.groups_id = [(4, school_group.id)]
                elif partner.partner_type == 'subpartner':
                    subpartner_group = self.env.ref('signup_page.group_subpartner_user')
                    user.groups_id = [(4, subpartner_group.id)]

        return user
