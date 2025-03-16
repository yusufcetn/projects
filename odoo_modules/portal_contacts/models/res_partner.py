from odoo import api, fields, models, _


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    def _compute_website_url(self):
        super(ResPartner, self)._compute_website_url()
        for partner in self:
            partner.website_url = "/my/contacts/%s" % partner.id