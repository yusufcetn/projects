from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo import _
import logging

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    # Fees fields
    fees_active = fields.Boolean(string="Add Extra Fees")
    fees_dom_fixed = fields.Float(string="Fixed Domestic Fees")
    fees_dom_var = fields.Float(string="Variable Domestic Fees (in %)")
    fees_int_fixed = fields.Float(string="Fixed International Fees")
    fees_int_var = fields.Float(string="Variable International Fees (in %)")


    def _compute_fees(self, amount, currency, country):
        self.ensure_one()

        fees = 0.0
        if self.fees_active:
            if country == self.company_id.country_id:
                fixed = self.fees_dom_fixed
                variable = self.fees_dom_var
            else:
                fixed = self.fees_int_fixed
                variable = self.fees_int_var
            fees = (amount * variable / 100.0 + fixed) / (1 - variable / 100.0)

        return fees

    @api.constrains('fees_dom_var', 'fees_int_var')
    def _check_fee_var_within_boundaries(self):
        for provider in self:
            if any(not 0 <= fee < 100 for fee in (provider.fees_dom_var, provider.fees_int_var)):
                raise ValidationError(_("Variable fees must always be positive and below 100%."))
