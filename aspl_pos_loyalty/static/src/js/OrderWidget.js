odoo.define('aspl_pos_loyalty.OrderWidget', function(require){
    "use strict";

    const OrderWidget = require("point_of_sale.OrderWidget");
    const Registries = require("point_of_sale.Registries");

    const aspl_OrderWidget = (OrderWidget) =>
        class extends OrderWidget{
            _updateSummary(){
                super._updateSummary(...arguments);
                var order = this.env.pos.get_order();
                if (!order.get_orderlines().length) {
                    return;
                }
                if(order.get_client()){
                    if(this.env.pos.loyalty_config && this.env.pos.loyalty_config.points_based_on == 'product'){
                        var total_points = this.get_points_from_product();
                        if(this.el.querySelector('.loyalty_info_cart .value')){
                            this.el.querySelector('.loyalty_info_cart .value').textContent = total_points;
                        }
                        order.set_loyalty_earned_point(total_points);
                        order.set_loyalty_earned_amount(order.get_loyalty_amount_by_point(total_points));
                    } else if(this.env.pos.loyalty_config && this.env.pos.loyalty_config.points_based_on == 'order') {
                        if(order.get_total_with_tax() >=  this.env.pos.loyalty_config.minimum_purchase
                                && this.env.pos.loyalty_config.point_calculation > 0){
                            var total_points = this._calculate_loyalty_by_order();
                            if(total_points > 0){
                                if(this.el.querySelector('.loyalty_info_cart .value')){
                                    this.el.querySelector('.loyalty_info_cart .value').textContent = total_points.toFixed(2);
                                }
                                order.set_loyalty_earned_point(total_points.toFixed(2));
                                order.set_loyalty_earned_amount(order.get_loyalty_amount_by_point(total_points));
                            }
                        } else if(order.get_total_with_tax() <  this.env.pos.loyalty_config.minimum_purchase){
                            order.set_loyalty_earned_point(0.00);
                        }
                    }
                }
            }
            get_points_from_product(){
                var self = this;
                var order = this.env.pos.get_order();
                var currentOrderline = order.get_orderlines()
                var total_points = 0.00
                _.each(currentOrderline, function(line){
                    var line_points = 0.00;
                    if(line.get_product().loyalty_point){
                        line_points = line.get_product().loyalty_point * line.get_quantity();
                        total_points += line_points;
                    } else if(line.get_product().pos_categ_id){
                        var cat_point = self._get_points_from_categ(line.get_product().pos_categ_id[0]);
                        if (cat_point){
                            line_points = cat_point * line.get_quantity();
                            total_points += line_points;
                        }
                    }
                })
                return total_points;
            }
            _calculate_loyalty_by_order(){
                var order = this.env.pos.get_order();
                return (order.get_total_with_tax() * this.env.pos.loyalty_config.point_calculation) / 100
            }
            _get_points_from_categ(categ_id){
                var category = this.env.pos.db.get_category_by_id(categ_id);
                if(category && category.loyalty_point){
                    return category.loyalty_point;
                } else if(category.parent_id){
                    this._get_points_from_categ(category.parent_id[0]);
                }
                return false;
            }
        };

    Registries.Component.extend(OrderWidget, aspl_OrderWidget);

    return aspl_OrderWidget;
})