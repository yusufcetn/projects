/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.PaymentFees = publicWidget.Widget.extend({
    selector: '#o_payment_methods',
    start: function () {
        this._super.apply(this, arguments);
        this.addFeeBadges();
    },

    addFeeBadges: function () {
        const paymentMethods = document.querySelectorAll('.o_payment_option_label');

        paymentMethods.forEach(methodLabel => {

            const paymentMethodInput = methodLabel.closest('.form-check').querySelector('input[type="radio"]');

            if (paymentMethodInput) {
                const paymentMethodContainer = methodLabel.closest('.d-flex.gap-2.flex-grow-1.me-auto');

                if (paymentMethodContainer) {

                    const feeBadge = document.createElement('span');
                    feeBadge.classList.add('badge', 'bg-secondary', 'fee-badge');
                    feeBadge.textContent = '$0.00 Fees';
                    feeBadge.style.padding = '5px 10px';
                    feeBadge.style.borderRadius = '5px';
                    feeBadge.style.marginLeft = '10px';

                    paymentMethodContainer.appendChild(feeBadge);

                    const paymentMethodType = paymentMethodInput.dataset.paymentMethodCode;

                    if (paymentMethodType) {
                        this.updateFee(feeBadge, paymentMethodType);
                    } else {
                        console.error('Payment method type not found');
                    }
                }
            } else {
                console.error('Payment method input not found');
            }
        });
    },

    updateFee: function (badgeElement, paymentMethodType) {

        jsonrpc('/payment/get_fee', {
            params: { payment_method: paymentMethodType }
        })
        .then(response => {
            const feeAmount = response.fee_amount;
            const currencySymbol = response.currency_symbol;
            const currencyPosition = response.currency_position;

            let formattedFee;
            if (currencyPosition === 'before') {
                formattedFee = `+${currencySymbol}${feeAmount.toFixed(2)} Fees`;
            } else {
                formattedFee = `+${feeAmount.toFixed(2)}${currencySymbol} Fees`;
            }

            badgeElement.textContent = formattedFee;
        })
        .catch(error => {
            console.error('Error fetching fee:', error);
        });
    }
});
