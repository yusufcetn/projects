from odoo import models, fields, api


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        processing_values = super()._get_specific_processing_values(processing_values)

        order = self.env['sale.order'].search([('name', '=', self.reference.split('-')[0])], limit=1)

        for transaction in self:
            if order:
                provider = self.provider_id
                if provider and provider.fees_active:
                    new_amount = transaction.amount
                    processing_values.update({'amount': new_amount})

        return processing_values

    def _stripe_prepare_payment_intent_payload(self):
        payload = super()._stripe_prepare_payment_intent_payload()

        order = self.env['sale.order'].search([('name', '=', self.reference.split('-')[0])], limit=1)

        for transaction in self:
            if order:
                provider = transaction.provider_id
                if provider and provider.fees_active:
                    fee_amount = provider._compute_fees(
                        amount=order.amount_untaxed + order.amount_tax,
                        currency=order.currency_id,
                        country=order.partner_id.country_id
                    )

                    payload['amount'] += int(fee_amount * 100)
                    transaction.amount += fee_amount

        return payload

    def _set_done(self, state_message=None, extra_allowed_states=()):
        res = super(PaymentTransaction, self)._set_done(state_message=state_message,
                                                        extra_allowed_states=extra_allowed_states)

        for transaction in self:

            if transaction.state == 'done':

                order = self.env['sale.order'].search([('name', '=', transaction.reference.split('-')[0])], limit=1)

                if order:
                    provider = transaction.provider_id
                    if provider and provider.fees_active:
                        existing_fee_line = self.env['sale.order.line'].search([
                            ('order_id', '=', order.id),
                            ('is_fee_line', '=', True)
                        ], limit=1)

                        if not existing_fee_line:
                            fee_amount = provider._compute_fees(
                                amount=order.amount_untaxed + order.amount_tax,
                                currency=order.currency_id,
                                country=order.partner_id.country_id
                            )

                            fee_product = self.env['product.product'].search([('default_code', '=', 'FEE_PRODUCT')],
                                                                             limit=1)

                            if fee_product:
                                self.env['sale.order.line'].create({
                                    'order_id': order.id,
                                    'product_id': fee_product.id,
                                    'product_uom_qty': 1,
                                    'price_unit': fee_amount,
                                    'name': 'Payment Processing Fee',
                                    'is_fee_line': True,
                                })

        return res
