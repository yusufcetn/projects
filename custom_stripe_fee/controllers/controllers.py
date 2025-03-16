from odoo import http
from odoo.http import request


class PaymentFeeController(http.Controller):

    @http.route('/payment/get_fee', type='json', auth='public', methods=['POST'], csrf=False, website=True)
    def get_fee(self, **kwargs):

        payment_method_code = kwargs.get('params').get('payment_method')

        if not payment_method_code:
            return {"error": "Missing payment method"}

        order = request.website.sale_get_order()

        if not order:
            return {"error": "Order not found"}

        payment_method_record = request.env['payment.method'].sudo().search([
            ('code', '=', payment_method_code)
        ], limit=1)

        if not payment_method_record:
            return {"error": "Payment method not found"}

        provider = request.env['payment.provider'].sudo().search([
            ('id', 'in', payment_method_record.provider_ids.ids)
        ], limit=1)

        if not provider:
            return {"error": "Payment provider not found"}

        fee_amount = 0

        if order:
            fee_amount = provider._compute_fees(
                amount=order.amount_untaxed + order.amount_tax,
                currency=order.currency_id,
                country=order.partner_id.country_id
            )

        return {
            'fee_amount': fee_amount,
            'currency_symbol': order.currency_id.symbol,
            'currency_position': order.currency_id.position
        }
