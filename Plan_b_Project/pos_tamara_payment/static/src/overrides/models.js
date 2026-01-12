import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentTamara } from "@pos_tamara_payment/app/payment_tamara";

register_payment_method("tamara", PaymentTamara);
