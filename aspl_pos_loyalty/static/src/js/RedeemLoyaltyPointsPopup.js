odoo.define('aspl_pos_loyalty.RedeemLoyaltyPointsPopup', function(require){
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class RedeemLoyaltyPointsPopup extends AbstractAwaitablePopup {
//	    show: function(options){
//	    	var self = this;
//	    	this.payment_self = options.payment_self;
//	    	this._super(options);
//	    	var order = self.pos.get_order();
//	    	var fields = _.find(this.pos.models,function(model){ return model.model === 'res.partner'; }).fields;
//	    	var params = {
//	    		model: 'res.partner',
//	    		method: 'search_read',
//	    		domain: [['id', '=', order.get_client().id]],
//	    		fields: fields,
//	    	}
//	    	rpc.query(params, {async: false})
//	    	.then(function(partner){
//	    		if(partner.length > 0){
//	    			var exist_partner = self.pos.db.get_partner_by_id(order.get_client().id);
//	    			_.extend(exist_partner, partner[0]);
//	    		}
//	    	});
//	    	$('body').off('keypress', self.payment_self.keyboard_handler);
//            $('body').off('keydown', self.payment_self.keyboard_keydown_handler);
//	    	window.document.body.removeEventListener('keypress',this.payment_self.keyboard_handler);
//	    	window.document.body.removeEventListener('keydown',this.payment_self.keyboard_keydown_handler);
//	    	self.renderElement();
//	    	$('.redeem_loyalty_input').focus();
//	    },
	    async confirm(){
	    	var self =this;
	    	var order = this.env.pos.get_order();
	    	var redeem_point_input = $('.redeem_loyalty_input');
	    	if(redeem_point_input.val() && $.isNumeric(redeem_point_input.val())
	    			&& Number(redeem_point_input.val()) > 0){
	    		var remaining_loyalty_points = order.get_client().remaining_loyalty_points - order.get_loyalty_redeemed_point();
	    		if(Number(redeem_point_input.val()) <= remaining_loyalty_points){
	    			var amount_to_redeem = (Number(redeem_point_input.val()) * self.env.pos.loyalty_config.to_amount) / self.env.pos.loyalty_config.points;
	    			if(amount_to_redeem <= (order.get_due() || order.get_total_with_tax())){
			    		if(self.env.pos.config.loyalty_journal_id){
//				    		var loyalty_cashregister = _.find(self.env.pos.cash_rounding, function(cashregister){
//				    			return cashregister.journal_id[0] === self.env.pos.config.loyalty_journal_id[0] ? cashregister : false;
//				    		});
//				    		if(loyalty_cashregister){
				    			order.add_paymentline(self.env.pos.payment_methods[0]);
				    			order.selected_paymentline.set_amount(amount_to_redeem);
				    			order.selected_paymentline.set_loyalty_point(Number(redeem_point_input.val()));
				    			order.selected_paymentline.set_freeze_line(true);
//				    			self.payment_self.reset_input();
//				    			self.payment_self.render_paymentlines();
				    			order.set_loyalty_redeemed_point(Number(order.get_loyalty_redeemed_point()) + Number(redeem_point_input.val()));
				    			order.set_loyalty_redeemed_amount(order.get_loyalty_amount_by_point(order.get_loyalty_redeemed_point()));
//				    			this.gui.close_popup();
//				    		}
			    		} else {
			    			alert(_t("Please configure Journal for Loyalty in Point of sale configuration."));
			    		}
	    			} else {
	    				alert(_t("Can not redeem more than order due."));
	    			}
	    		} else {
	    			alert(_t("Input must be <= "+ remaining_loyalty_points));
	    		}
	    	}
	    	else {
	    		alert(_t("Invalid Input"));
	    	}
            return super.confirm();
	    }
	    _cancelAtEscape(event) {
	    	var self = this;
	    	var order = self.env.pos.get_order();
	    	if(self.el.querySelector('.redeem_loyalty_input')){
		    	self.el.querySelector('.redeem_loyalty_input').addEventListener('keyup', function(e){
		    		if($.isNumeric($(this).val())){
		    			var remaining_loyalty_points = order.get_client().remaining_loyalty_points - order.get_loyalty_redeemed_point();
		    			var amount = order.get_loyalty_amount_by_point(Number($(this).val()));
		    			$('.point_to_amount').text(Intl.NumberFormat('en-US').format(amount));
		    			if(Number($(this).val()) > remaining_loyalty_points){
		    				alert("Can not redeem more than your remaining points");
		    				$(this).val(0);
		    				$('.point_to_amount').text('0.00');
		    			}
		    			if(amount > (order.get_due() || order.get_total_with_tax())){
		    				alert("Loyalty Amount exceeding Due Amount");
		    				$(this).val(0);
		    				$('.point_to_amount').text('0.00');
		    			}
		    		} else {
		    			$('.point_to_amount').text('0.00');
		    		}
		    	});
	    	}
            return super._cancelAtEscape(event)
	    }
//	    cancel(){
//	    	window.document.body.addEventListener('keypress',this.payment_self.keyboard_handler);
//	    	window.document.body.addEventListener('keydown',this.payment_self.keyboard_keydown_handler);
//	    }
    }
    RedeemLoyaltyPointsPopup.template = 'RedeemLoyaltyPointsPopup';

    RedeemLoyaltyPointsPopup.defaultProps = {
//        payment_self: {},
    }

    Registries.Component.add(RedeemLoyaltyPointsPopup);

    return RedeemLoyaltyPointsPopup;
});