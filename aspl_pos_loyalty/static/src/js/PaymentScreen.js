odoo.define('aspl_pos_loyalty.PaymentScreen', function(require){
    "use strict";

    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const Registries = require("point_of_sale.Registries");
    const { Gui } = require('point_of_sale.Gui');
    var core = require('web.core');
    var _t = core._t;

    const aspl_PaymentScreen = (_PaymentScreen) =>
        class extends _PaymentScreen{
            _click_js_redeem_loyalty(){
                var self = this;
                var order = self.env.pos.get_order();
                if(order.get_client()){
                    if(order.get_client().total_remaining_points > 0){
                        self.click_redeem_loyalty();
                    } else {
                        Gui.showPopup('ErrorPopup',{
                            'title': _t("Loyalty Points"),
                            'body': _t(order.get_client().name + " have 0 points to redeem."),
                        })
                    }
                }

            }
            click_redeem_loyalty(){
                var order = this.env.pos.get_order();
                if(order.get_client()){

                    Gui.showPopup("RedeemLoyaltyPointsPopup");
                }
            }
//            payment_input: function(input) {
//                var self = this;
//                var order = this.pos.get_order();
//                if(order.selected_paymentline.get_freeze_line()){
//                    return
//                }
//                this._super(input);
//            }
        }

    Registries.Component.extend(PaymentScreen, aspl_PaymentScreen);

    return aspl_PaymentScreen;

});