import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);

        // Connect to WebSocket to receive Tamara payment notifications
        this.data.connectWebSocket("TAMARA_LATEST_RESPONSE", (payload) => {
            // Only process notifications for this POS config
            if (payload.config_id === this.config.id) {
                console.log('Tamara WebSocket notification received:', payload);

                // Find the payment line by Tamara order_id
                const paymentLine = this.models["pos.payment"].find(
                    line => line.uiState?.tamaraOrderId === payload.order_id
                );

                if (paymentLine &&
                    !paymentLine.is_done() &&
                    paymentLine.get_payment_status() !== 'retry') {

                    // Forward notification to payment interface handler
                    paymentLine.payment_method_id.payment_terminal
                        .handleTamaraStatusResponse(paymentLine, payload);
                } else {
                    console.log('No matching payment line found or payment already processed');
                }
            }
        });
    },
});
