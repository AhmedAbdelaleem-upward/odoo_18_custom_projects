import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class PaymentTamara extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
    }

    /**
     * Send payment request to Tamara
     * Called when cashier selects Tamara payment method
     */
    async send_payment_request(uuid) {
        super.send_payment_request(uuid);

        const order = this.pos.get_order();
        const line = order.payment_ids.find(pl => pl.uuid === uuid);

        if (!line) {
            return false;
        }

        if (line.amount < 0) {
            // Handle Refund
            return this._tamara_process_refund(line);
        }

        // Step 1: Get customer phone number
        const phoneNumber = await this._ask_phone_number();
        if (!phoneNumber) {
            line.set_payment_status('retry');
            return false;
        }

        // Step 2: Create Tamara checkout session and send SMS
        return this._tamara_create_checkout(line, phoneNumber);
    }

    /**
     * Cancel pending payment
     * Called when cashier cancels the payment
     */
    async send_payment_cancel(order, uuid) {
        super.send_payment_cancel(order, uuid);

        const line = order.payment_ids.find(pl => pl.uuid === uuid);
        if (line && line.uiState?.tamaraOrderId) {
            try {
                await this.pos.data.silentCall(
                    'pos.payment.method',
                    'proxy_tamara_cancel',
                    [[this.payment_method_id.id], { order_id: line.uiState.tamaraOrderId }]
                );
                console.log('Tamara payment cancelled:', line.uiState.tamaraOrderId);
            } catch (error) {
                console.error('Failed to cancel Tamara payment:', error);
            }
        }

        return Promise.resolve();
    }

    /**
     * Prompt cashier to enter customer phone number
     * Returns phone number or null if cancelled
     */
    async _ask_phone_number() {
        // Use browser prompt for simplicity
        const phone = prompt(_t("Enter customer phone number (with country code, e.g., +966501234567):"));

        if (!phone) {
            return null;
        }

        // Basic validation: should have 10-15 digits
        const cleaned = phone.replace(/[\s-]/g, '');
        if (!/^\+?[0-9]{10,15}$/.test(cleaned)) {
            this._show_error(_t('Invalid phone number format. Please include country code.'));
            return null;
        }

        return cleaned;
    }

    /**
     * Process refund for negative amount
     */
    async _tamara_process_refund(line) {
        // Step 1: Ask for original Tamara Order ID
        const orderId = await this._ask_tamara_order_id();
        if (!orderId) {
            line.set_payment_status('retry');
            return false;
        }

        // Step 2: Call backend to refund
        try {
            const response = await this.pos.data.silentCall(
                'pos.payment.method',
                'proxy_tamara_refund',
                [[this.payment_method_id.id], {
                    'order_id': orderId,
                    'total_amount': Math.abs(line.amount),
                    'currency': this.pos.currency.name,
                    'comment': 'POS Refund'
                }]
            );

            if (response.error) {
                this._show_error(response.error.message);
                line.set_payment_status('retry');
                return false;
            }

            // Success
            if (response.demo_mode) {
                this._show_info(_t('🎭 DEMO MODE: Refund approved successfully!'));
            } else {
                this._show_info(_t('Refund processed successfully! ID: %s', response.refund_id));
            }

            line.transaction_id = response.refund_id || orderId;
            line.set_payment_status('done');
            return true;

        } catch (error) {
            console.error('Tamara refund failed:', error);
            this._handle_odoo_connection_failure(line);
            return false;
        }
    }

    /**
     * Prompt for Tamara Order ID
     */
    async _ask_tamara_order_id() {
        const orderId = prompt(_t("Enter original Tamara Order ID for refund (e.g., 53435717-...):"));
        if (!orderId) return null;
        return orderId.trim();
    }

    /**
     * Create Tamara checkout session via backend
     * Sends SMS with payment link to customer
     */
    async _tamara_create_checkout(line, phoneNumber) {
        const order = this.pos.get_order();

        const data = {
            phone_number: phoneNumber,
            amount: line.amount,
            currency: this.pos.currency.name,
            order_reference: `${order.uuid}--${order.session_id.id}`
        };

        line.set_payment_status('waitingCard');

        try {
            const response = await this.pos.data.silentCall(
                'pos.payment.method',
                'proxy_tamara_checkout',
                [[this.payment_method_id.id], data]
            );

            if (response.error) {
                const errorMsg = response.error.message || _t('Payment request failed');
                this._show_error(errorMsg);
                line.set_payment_status('retry');
                return false;
            }

            // Store Tamara order_id for later reference
            if (!line.uiState) {
                line.uiState = {};
            }
            line.uiState.tamaraOrderId = response.order_id;

            console.log('Tamara checkout created:', response.order_id);

            // Show success message to cashier (different for demo vs real mode)
            if (response.demo_mode) {
                this._show_info(_t('🎭 DEMO MODE: Simulating payment flow. Webhook will arrive in a few seconds...'));
            } else {
                this._show_info(_t('SMS sent to customer. Waiting for payment confirmation...'));
            }

            // Wait for webhook notification
            return this.waitForPaymentConfirmation(line);

        } catch (error) {
            console.error('Tamara checkout error:', error);
            this._handle_odoo_connection_failure(line);
            return false;
        }
    }

    /**
     * Wait for payment confirmation via webhook
     * Returns promise that resolves when webhook is received
     */
    waitForPaymentConfirmation(line) {
        return new Promise((resolve) => {
            // Store resolver to be called by webhook handler
            this.paymentLineResolvers[line.uuid] = resolve;

            // Start polling timer (every 5 seconds)
            const pollIntervalMs = 5000;
            const pollTimer = setInterval(async () => {
                if (!this.paymentLineResolvers[line.uuid]) {
                    clearInterval(pollTimer);
                    return;
                }

                try {
                    const response = await this.pos.data.silentCall(
                        'pos.payment.method',
                        'proxy_tamara_poll',
                        [[this.payment_method_id.id], { order_id: line.uiState.tamaraOrderId }]
                    );

                    // Check if we got a final status
                    if (response && ['approved', 'declined', 'expired', 'failed', 'canceled'].includes(response.status)) {
                        console.log('Tamara polling status update:', response);
                        this.handleTamaraStatusResponse(line, response);
                    }
                } catch (error) {
                    console.error('Tamara polling failed:', error);
                    // Continue polling even if one request fails
                }
            }, pollIntervalMs);

            // Set strict timeout: 5 minutes
            const timeoutMs = 300000; // 5 minutes
            setTimeout(() => {
                clearInterval(pollTimer); // Stop polling
                if (this.paymentLineResolvers[line.uuid]) {
                    // Timeout reached, payment not completed
                    delete this.paymentLineResolvers[line.uuid];
                    this._show_error(_t('Payment timeout. Customer did not complete payment within 5 minutes.'));
                    line.set_payment_status('retry');
                    resolve(false);
                }
            }, timeoutMs);
        });
    }

    /**
     * Handle webhook notification response
     * Called by WebSocket listener when payment status updates
     */
    handleTamaraStatusResponse(line, notification) {
        console.log('Tamara status response:', notification);

        const isSuccess = notification.status === 'approved';

        if (isSuccess) {
            // Payment approved
            line.transaction_id = notification.transaction_id || notification.order_id;
            line.set_payment_status('done');
            this._show_info(_t('Payment approved successfully!'));
        } else {
            // Payment declined, expired, or failed
            const errorMsg = this._get_error_message(notification.status);
            this._show_error(errorMsg);
            line.set_payment_status('retry');
        }

        // Resolve waiting promise
        const resolver = this.paymentLineResolvers[line.uuid];
        if (resolver) {
            delete this.paymentLineResolvers[line.uuid];
            resolver(isSuccess);
        } else {
            // No waiting promise, update payment line directly
            line.handle_payment_response(isSuccess);
        }
    }

    /**
     * Get user-friendly error message for payment status
     */
    _get_error_message(status) {
        const messages = {
            'declined': _t('Payment was declined by customer or Tamara.'),
            'expired': _t('Payment session expired. Please try again.'),
            'failed': _t('Payment failed. Please try again.'),
            'canceled': _t('Payment was cancelled.'),
        };
        return messages[status] || _t('Payment unsuccessful. Status: %s', status);
    }

    /**
     * Handle Odoo connection failure
     */
    _handle_odoo_connection_failure(line) {
        if (line && !line.is_done()) {
            line.set_payment_status('retry');
        }
        this._show_error(
            _t('Could not connect to the Odoo server. Please check your internet connection and try again.')
        );
    }

    /**
     * Show error dialog to cashier
     */
    _show_error(msg, title = null) {
        if (!title) {
            title = _t("Tamara Payment Error");
        }
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }

    /**
     * Show info dialog to cashier
     */
    _show_info(msg, title = null) {
        if (!title) {
            title = _t("Tamara Payment");
        }
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }
}
