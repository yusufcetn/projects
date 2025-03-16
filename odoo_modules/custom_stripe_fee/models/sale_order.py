from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_provider_fee = fields.Monetary(string="Payment Provider Fee", currency_field='currency_id', compute='_compute_payment_provider_fee')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_fee_line = fields.Boolean(string="Is Fee Line")