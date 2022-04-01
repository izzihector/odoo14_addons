odoo.define('aspl_pos_loyalty.OrderReceipt', function(require){
    "use strict";

    const OrderReceipt = require("point_of_sale.OrderReceipt");
    const Registries = require("point_of_sale.Registries");

    const aspl_OrderReceipt = (OrderReceipt) =>
        class extends OrderReceipt{
        };

    Registries.Component.extend(OrderReceipt, aspl_OrderReceipt);

    return aspl_OrderReceipt;
})