odoo.define('aspl_pos_loyalty.loyaltyConfig', function(require){
    "use strict";

    var models = require('point_of_sale.models');
    var rpc = require('web.rpc');
    var DB = require('point_of_sale.DB');

    models.load_fields("res.partner", ['remaining_loyalty_points', 'remaining_loyalty_amount', 'loyalty_points_earned', 'total_remaining_points']);
	models.load_fields("product.product", ['loyalty_point']);
	models.load_fields("pos.category", ['loyalty_point']);

    var _super_posmodel = models.PosModel;
	models.PosModel = models.PosModel.extend({
		load_server_data: function(){
			var self = this;
			var loaded = _super_posmodel.prototype.load_server_data.call(this);
			var domain = [];
			var fields = [];
			loaded.then(function(){
				var params = {
					model: 'pos.order',
					method: 'loyalty_config_read',
					args: [],
				}
				rpc.query(params)
		    	.then(function(loyalty_config){
		    		if(loyalty_config && loyalty_config[0]){
		    			self.loyalty_config = loyalty_config[0];
		    		}
		    	})
			})
			return loaded
		},
	});

	var _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({
    	initialize: function(attributes,options){
        	_super_Order.initialize.apply(this, arguments);
        	this.set({
        		loyalty_redeemed_point: 0.00,
        		loyalty_earned_point: 0.00,
        	})
    	},
    	set_loyalty_redeemed_point: function(val){
    		this.set('loyalty_redeemed_point', Number(val).toFixed(2));
    	},
    	get_loyalty_redeemed_point: function(){
    		return this.get('loyalty_redeemed_point') || 0.00;
    	},
    	set_loyalty_redeemed_amount: function(val){
    		this.set('loyalty_redeemed_amount', val);
    	},
    	get_loyalty_redeemed_amount: function(){
    		return this.get('loyalty_redeemed_amount') || 0.00;
    	},
    	set_loyalty_earned_point: function(val){
    	    console.log('val', val);
    		this.set('loyalty_earned_point', val);
    	},
    	get_loyalty_earned_point: function(){
    		return this.get('loyalty_earned_point') || 0.00;
    	},
    	set_loyalty_earned_amount: function(val){
    		this.set('loyalty_earned_amount', val);
    	},
    	get_loyalty_earned_amount: function(){
    		return this.get('loyalty_earned_amount') || 0.00;
    	},
    	export_as_JSON: function() {
            var self = this;
        	var new_val = {};
            var orders = _super_Order.export_as_JSON.call(this);
            new_val = {
            	loyalty_redeemed_point: this.get_loyalty_redeemed_point() || false,
            	loyalty_redeemed_amount: this.get_loyalty_redeemed_amount() || false,
            	loyalty_earned_point: this.get_loyalty_earned_point() || false,
            	loyalty_earned_amount: this.get_loyalty_earned_amount() || false,
            }
            $.extend(orders, new_val);
            return orders;
    	},
    	remove_paymentline: function(line){
    		this.set_loyalty_redeemed_point(this.get_loyalty_redeemed_point() - line.get_loyalty_point());
    		this.set_loyalty_redeemed_amount(this.get_loyalty_amount_by_point(this.get_loyalty_redeemed_point()));
    		_super_Order.remove_paymentline.apply(this, arguments);
    	},
    	get_total_loyalty_points: function(){
    		var temp = 0.00
    		if(this.get_client()){
	    		temp = Number(this.get_client().total_remaining_points)
	    				+ Number(this.get_loyalty_earned_point())
	    				- Number(this.get_loyalty_redeemed_point())
    		}
    		return temp.toFixed(2)
    	},
    	export_for_printing: function(){
    		var self = this;
    		var orders = _super_Order.export_for_printing.call(this);
    		var new_val = {
    			total_points: this.get_total_loyalty_points() || false,
    			earned_points: this.get_loyalty_earned_point() || false,
    			redeem_points: this.get_loyalty_redeemed_point() || false,
    			client_points: this.get_client() ? this.get_client().total_remaining_points.toFixed(2) : false,
    		};
    		$.extend(orders, new_val);
            return orders;
    	},
    	get_loyalty_amount_by_point: function(point){
	    	return (point * this.pos.loyalty_config.to_amount) / this.pos.loyalty_config.points;
	    },
    });

    var _super_paymentline = models.Paymentline.prototype;
    models.Paymentline = models.Paymentline.extend({
       initialize: function(attributes, options) {
           var self = this;
           _super_paymentline.initialize.apply(this, arguments);
           this.set({
        		   loyalty_point: 0,
        		   loyalty_amount: 0.00,
           });
        },
        set_loyalty_point: function(points){
        	this.set('loyalty_point', points)
        },
        get_loyalty_point: function(){
        	return this.get('loyalty_point')
        },
        set_loyalty_amount: function(amount){
        	this.set('loyalty_amount', amount)
        },
        get_loyalty_amount: function(){
        	return this.get('loyalty_amount')
        },
        set_freeze_line: function(freeze_line){
        	this.set('freeze_line', freeze_line)
        },
        get_freeze_line: function(){
        	return this.get('freeze_line')
        },
    });

    DB.include({
		add_partners: function(partners){
			var self = this;
			for(var i = 0, len = partners.length; i < len; i++){
	            var partner = partners[i];
	            var old_partner = this.partner_by_id[partner.id];
	            if(partners && old_partner && partner.total_remaining_points !== old_partner.total_remaining_points){
	            	old_partner['total_remaining_points'] = partner.total_remaining_points;
	            }
			}
			return this._super(partners);
		},
	});
});