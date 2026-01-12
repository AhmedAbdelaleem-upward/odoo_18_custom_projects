/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {rpc} from "@web/core/network/rpc";
import PaymentForm from "@payment/js/payment_form";

PaymentForm.include({
    /**
     * Prepare the inline form for Tamara provider.
     * Sets the payment flow to 'direct' for inline processing.
     *
     * @override
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'tamara') {
            return this._super(...arguments);
        }
        // Set flow to 'direct' for inline processing
        this._setPaymentFlow('direct');
    },

    /**
     * Process direct payment flow for Tamara.
     * Gets the selected payment state from the inline form and creates a transaction.
     *
     * @override
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode) {
        if (providerCode !== 'tamara') {
            return this._super(...arguments);
        }

        // Get the selected payment state from the inline form
        const simulatedState = document.getElementById('tamara_simulated_payment_state')?.value || 'success';
        const customerInput = document.querySelector('input[name="customer_input"]')?.value || 'Test Data';

        // Create transaction with simulated data
        return rpc(this.paymentContext['transactionRoute'], {
            ...this._prepareTransactionRouteParams(
                providerCode, paymentOptionId, paymentMethodCode, 'direct'
            ),
        }).then(processingValues => {
            // Simulate immediate payment processing
            return rpc('/payment/tamara/process', {
                'reference': processingValues.reference,
                'payment_outcome': simulatedState,
                'payment_details': customerInput,
            });
        }).then(() => {
            window.location = this.paymentContext['landingRoute'];
        }).catch(error => {
            error.event.preventDefault();
            this._displayErrorDialog(_t("Payment Error"), error.data?.message || error.message);
            this._enableButton();
        });
    },
});
