// odoo.define('pways_quotations_comparison_dashboard.Dashboard', function (require) {
// "use strict";

// var AbstractAction = require('web.AbstractAction');
// var ajax = require('web.ajax');
// var core = require('web.core');
// var rpc = require('web.rpc');
// var session = require('web.session');
// var utils = require('web.utils');
// var web_client = require('web.web_client');
// var _t = core._t;
// var QWeb = core.qweb;

// var RFQDashboard = AbstractAction.extend({
//     template: 'RFQDashboard',
//     events: {
//         'click  .remove_line': '_remove_line',
// /*        'click  .show_product': '_show_product',*/
//         'click  .conform_order': '_conform_order',
//         'click .update_tender': '_update_tender',
//         'change #selection_type': 'onChangeSelectionType',
//     },

//     init: function(parent, options) {
//         this._super(parent, options);
//         this.reqisition_id = options.context.reqisition_id;
//         this.purchase_ids = [];
//         this.select_type = "";
//         if (!this.reqisition_id)
//         {
//             this.reqisition_id = utils.get_cookie('id');
//         }
//     },
//     willStart: function() {
//         var self = this;
//         return $.when(ajax.loadLibs(this), this._super()).then(function() {
//             return self.fetch_data();
//         });
//     },
//     fetch_data: function () {
//         var self = this;
//         var def1 =  this._rpc({
//             model: 'purchase.requisition',
//             method: 'get_purchase_line_data',
//             args: [this.select_type, this.reqisition_id],
//         }).then(function(result) {
//             self.purchase_ids = result
//         });
//         return $.when(def1);
//     },
//     onChangeSelectionType: function(events) {
//         var self = this;
//         var option = $(events.target).val();
//         this.select_type = option
//         var def1 =  this._rpc({
//             model: 'purchase.requisition',
//             method: 'get_purchase_line_data',
//             args: [option, self.reqisition_id],
//             }).then(function(result) {
//                 self.purchase_ids = result;
//                 self.render_dashboards(
//                     result, 
//                     result.record_line_ids, 
//                     result.partner_ids, 
//                     result.total, 
//                     result.length, 
//                     result.option, 
//                     result.min_total_vendor, 
//                     result.min_delivery_vendor,
//                     result.reqisition_name,
//                 );
//             });
//         return $.when(def1);
//     },
//     /*_show_product: function () {
//         var self = this;
//         $(".show_product").click(function() {
//             self.$el.popover('dispose');
//             var vendor = $(this).attr("vendor-id");
//             var product = $(this).attr("product-id");
//             var prize = $(this).attr("prize-id");
//             var min_date = $(this).attr("min-date-id");
//             var min_date_vendor = $(this).attr("vendor-min-id");
//             const $content = $(QWeb.render('MessageTemplate', {
//                 'vendor': vendor, 
//                 'product': product, 
//                 'prize': prize, 
//                 'min_date_vendor': min_date_vendor, 
//                 'min_date': min_date,
//             }));
//             const options = {
//                 content: $content,
//                 container: $('.fa-info'),
//                 html: true,
//                 placement: 'top',
//                 title: _t(product),
//                 delay: {'show': 0, 'hide': 100 },
//             };
//             self.$el.popover(options);
//         });
//     },*/
//     _conform_order:function () {
//         var self = this;
//         $(".conform_order").click(function() {
//             var gen = $(this).attr("data-id");
//             return rpc.query({
//                 model: 'purchase.requisition',
//                 method: 'confirm_order_action',
//                 args: [gen],
//             }).then(function(result) {
//                 var action = {
//                     'name': 'Dashboard',
//                     'type': 'ir.actions.client',
//                     'tag': 'compare_dashboard',
//                     'context': {'reqisition_id': self.reqisition_id},
//                 };

//                 return self.do_action(action);
//             });
//         });
//     },
//     _update_tender: function(ev) {
//         var self = this;
//         var purchase_id = $(ev.currentTarget).data('id');
//         var req_id = self.reqisition_id;
    
//         // Show loading indicator
//         self.$('.o_rfq_dashboard').html('<div class="spinner-border" role="status"><span class="sr-only">Loading...</span></div>');
    
//         return rpc.query({
//             model: 'purchase.requisition',
//             method: 'update_tender_action',
//             args: [req_id, purchase_id],
//         }).then(function (result) {
//             if (result) {
//                 // Show success notification
//                 self.displayNotification({
//                     title: _t("Success"),
//                     message: _t("Tender updated with prices from selected RFQ"),
//                     type: 'success',
//                     sticky: false,
//                 });
                
//                 // Refresh the dashboard
//                 self.fetch_data().then(function() {
//                     self.render_dashboards(
//                         self.purchase_ids, 
//                         self.purchase_ids.record_line_ids, 
//                         self.purchase_ids.partner_ids, 
//                         self.purchase_ids.total, 
//                         self.purchase_ids.length, 
//                         self.purchase_ids.option, 
//                         self.purchase_ids.min_total_vendor, 
//                         self.purchase_ids.min_delivery_vendor,
//                         self.purchase_ids.requisition_name
//                     );
//                 });
//             } else {
//                 // Show error if result is false
//                 self.displayNotification({
//                     title: _t("Error"),
//                     message: _t("Failed to update tender. Please try again."),
//                     type: 'danger',
//                     sticky: true,
//                 });
//             }
//         }).catch(function(error) {
//             console.error('Error updating tender:', error);
            
//             // Show error notification
//             self.displayNotification({
//                 title: _t("Error"),
//                 message: _t("An error occurred while updating the tender."),
//                 type: 'danger',
//                 sticky: true,
//             });
            
//             // Restore previous view
//             self.render_dashboards(
//                 self.purchase_ids, 
//                 self.purchase_ids.record_line_ids, 
//                 self.purchase_ids.partner_ids, 
//                 self.purchase_ids.total, 
//                 self.purchase_ids.length, 
//                 self.purchase_ids.option, 
//                 self.purchase_ids.min_total_vendor, 
//                 self.purchase_ids.min_delivery_vendor,
//                 self.purchase_ids.requisition_name
//             );
//         });
//     },
//     _remove_line: function () {
//         var self = this;
//         $(".remove_line").click(function() {
//             var gen = $(this).attr("data-id");
//             return rpc.query({
//                 model: 'purchase.requisition',
//                 method: 'remove_line_action',
//                 args: [gen, self.reqisition_id],
//             }).then(function(result) {
//                 var action = {
//                     'name': 'Dashboard',
//                     'type': 'ir.actions.client',
//                     'tag': 'compare_dashboard',
//                     'context': {'reqisition_id': self.reqisition_id},
//                 };
//                 return self.do_action(action);
//             });
//         });
//     },
//     start: function() {
//         utils.set_cookie("id", this.reqisition_id);
//         var self = this;  
//         return this._super().then(function() {
//             self.render_dashboards(
//                 self.purchase_ids, 
//                 self.purchase_ids.record_line_ids, 
//                 self.purchase_ids.partner_ids, 
//                 self.purchase_ids.total, 
//                 self.purchase_ids.length, 
//                 self.purchase_ids.option, 
//                 self.purchase_ids.min_total_vendor, 
//                 self.purchase_ids.min_delivery_vendor, 
//                 self.purchase_ids.reqisition_name
//             );
//         });
//     },
//     render_dashboards: function (res, record_line_ids, partner_ids, total, length, option, min_total_vendor, min_delivery_vendor, reqisition_name) {
//         this.$('.o_rfq_dashboard').html(QWeb.render('RFQCompareTable', {
//             widget: res, 
//             'record_line_ids': record_line_ids, 
//             'partner_ids': partner_ids, 
//             'total': total, 
//             'length': length, 
//             'option': option, 
//             'min_total_vendor': min_total_vendor, 
//             'min_delivery_vendor': min_delivery_vendor, 
//             'reqisition_name': reqisition_name
//         }));
//     }
// });

// core.action_registry.add('compare_dashboard', RFQDashboard);

// return RFQDashboard;

// });

odoo.define('pways_quotations_comparison_dashboard.Dashboard', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var utils = require('web.utils');
    var web_client = require('web.web_client');
    var _t = core._t;
    var QWeb = core.qweb;

    var RFQDashboard = AbstractAction.extend({
        template: 'RFQDashboard',
        events: {
            'click .remove_line': '_remove_line',
            'click .conform_order': '_conform_order',
            'click .update_tender': '_update_tender',
            'change #selection_type': 'onChangeSelectionType',
        },

        init: function(parent, options) {
            this._super(parent, options);
            this.reqisition_id = options.context.reqisition_id;
            this.purchase_ids = [];
            this.select_type = "";
            if (!this.reqisition_id) {
                this.reqisition_id = utils.get_cookie('id');
            }
        },

        willStart: function() {
            var self = this;
            return $.when(ajax.loadLibs(this), this._super()).then(function() {
                return self.fetch_data();
            });
        },

        fetch_data: function () {
            var self = this;
            var def1 = this._rpc({
                model: 'purchase.requisition',
                method: 'get_purchase_line_data',
                args: [this.select_type, this.reqisition_id],
            }).then(function(result) {
                self.purchase_ids = result;
            });
            return $.when(def1);
        },

        onChangeSelectionType: function(events) {
            var self = this;
            var option = $(events.target).val();
            this.select_type = option;
            var def1 = this._rpc({
                model: 'purchase.requisition',
                method: 'get_purchase_line_data',
                args: [option, self.reqisition_id],
            }).then(function(result) {
                self.purchase_ids = result;
                self.render_dashboards(
                    result,
                    result.record_line_ids,
                    result.partner_ids,
                    result.total,
                    result.length,
                    result.option,
                    result.min_total_vendor,
                    result.min_delivery_vendor,
                    result.requisition_name
                );
            });
            return $.when(def1);
        },

        _conform_order: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var self = this;
            var purchase_id = parseInt($(ev.currentTarget).attr("data-id"));
            
            return rpc.query({
                model: 'purchase.requisition',
                method: 'confirm_order_action',
                args: [purchase_id],
            }).then(function(result) {
                // Refresh the dashboard
                return self.fetch_data().then(function() {
                    self.render_dashboards(
                        self.purchase_ids,
                        self.purchase_ids.record_line_ids,
                        self.purchase_ids.partner_ids,
                        self.purchase_ids.total,
                        self.purchase_ids.length,
                        self.purchase_ids.option,
                        self.purchase_ids.min_total_vendor,
                        self.purchase_ids.min_delivery_vendor,
                        self.purchase_ids.requisition_name
                    );
                    
                    self.displayNotification({
                        title: _t("Success"),
                        message: _t("Order confirmed successfully"),
                        type: 'success',
                        sticky: false,
                    });
                });
            }).catch(function(error) {
                console.error('Error confirming order:', error);
                self.displayNotification({
                    title: _t("Error"),
                    message: _t("Failed to confirm order. Please try again."),
                    type: 'danger',
                    sticky: true,
                });
            });
        },

        _update_tender: function(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var self = this;
            var purchase_id = parseInt($(ev.currentTarget).data('id'));
            var req_id = self.reqisition_id;

            // Show loading indicator
            self.$('.o_rfq_dashboard').html('<div class="text-center p-5"><i class="fa fa-spinner fa-spin fa-3x"></i><br/>Loading...</div>');

            return rpc.query({
                model: 'purchase.requisition',
                method: 'update_tender_action',
                args: [req_id, purchase_id],
            }).then(function (result) {
                if (result) {
                    self.displayNotification({
                        title: _t("Success"),
                        message: _t("Tender updated with prices from selected RFQ"),
                        type: 'success',
                        sticky: false,
                    });

                    // Refresh the dashboard
                    return self.fetch_data().then(function() {
                        self.render_dashboards(
                            self.purchase_ids,
                            self.purchase_ids.record_line_ids,
                            self.purchase_ids.partner_ids,
                            self.purchase_ids.total,
                            self.purchase_ids.length,
                            self.purchase_ids.option,
                            self.purchase_ids.min_total_vendor,
                            self.purchase_ids.min_delivery_vendor,
                            self.purchase_ids.requisition_name
                        );
                    });
                } else {
                    self.displayNotification({
                        title: _t("Error"),
                        message: _t("Failed to update tender. Please try again."),
                        type: 'danger',
                        sticky: true,
                    });
                    
                    // Restore previous view
                    self.render_dashboards(
                        self.purchase_ids,
                        self.purchase_ids.record_line_ids,
                        self.purchase_ids.partner_ids,
                        self.purchase_ids.total,
                        self.purchase_ids.length,
                        self.purchase_ids.option,
                        self.purchase_ids.min_total_vendor,
                        self.purchase_ids.min_delivery_vendor,
                        self.purchase_ids.requisition_name
                    );
                }
            }).catch(function(error) {
                console.error('Error updating tender:', error);
                self.displayNotification({
                    title: _t("Error"),
                    message: _t("An error occurred while updating the tender."),
                    type: 'danger',
                    sticky: true,
                });
                
                // Restore previous view
                self.render_dashboards(
                    self.purchase_ids,
                    self.purchase_ids.record_line_ids,
                    self.purchase_ids.partner_ids,
                    self.purchase_ids.total,
                    self.purchase_ids.length,
                    self.purchase_ids.option,
                    self.purchase_ids.min_total_vendor,
                    self.purchase_ids.min_delivery_vendor,
                    self.purchase_ids.requisition_name
                );
            });
        },

        _remove_line: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var self = this;
            var line_id = parseInt($(ev.currentTarget).attr("data-id"));
            
            console.log('Removing line with ID:', line_id);
            
            return rpc.query({
                model: 'purchase.requisition',
                method: 'remove_line_action',
                args: [line_id, self.reqisition_id],
            }).then(function(result) {
                if (result) {
                    // Refresh the dashboard
                    return self.fetch_data().then(function() {
                        self.render_dashboards(
                            self.purchase_ids,
                            self.purchase_ids.record_line_ids,
                            self.purchase_ids.partner_ids,
                            self.purchase_ids.total,
                            self.purchase_ids.length,
                            self.purchase_ids.option,
                            self.purchase_ids.min_total_vendor,
                            self.purchase_ids.min_delivery_vendor,
                            self.purchase_ids.requisition_name
                        );
                        
                        self.displayNotification({
                            title: _t("Success"),
                            message: _t("Line removed successfully"),
                            type: 'success',
                            sticky: false,
                        });
                    });
                } else {
                    self.displayNotification({
                        title: _t("Error"),
                        message: _t("Failed to remove line. Please try again."),
                        type: 'danger',
                        sticky: true,
                    });
                }
            }).catch(function(error) {
                console.error('Error removing line:', error);
                self.displayNotification({
                    title: _t("Error"),
                    message: _t("An error occurred while removing the line."),
                    type: 'danger',
                    sticky: true,
                });
            });
        },

        start: function() {
            utils.set_cookie("id", this.reqisition_id);
            var self = this;
            return this._super().then(function() {
                self.render_dashboards(
                    self.purchase_ids,
                    self.purchase_ids.record_line_ids,
                    self.purchase_ids.partner_ids,
                    self.purchase_ids.total,
                    self.purchase_ids.length,
                    self.purchase_ids.option,
                    self.purchase_ids.min_total_vendor,
                    self.purchase_ids.min_delivery_vendor,
                    self.purchase_ids.requisition_name
                );
            });
        },

        render_dashboards: function (res, record_line_ids, partner_ids, total, length, option, min_total_vendor, min_delivery_vendor, requisition_name) {
            this.$('.o_rfq_dashboard').html(QWeb.render('RFQCompareTable', {
                widget: res,
                'record_line_ids': record_line_ids,
                'partner_ids': partner_ids,
                'total': total,
                'length': length,
                'option': option,
                'min_total_vendor': min_total_vendor,
                'min_delivery_vendor': min_delivery_vendor,
                'requisition_name': requisition_name
            }));
        }
    });

    core.action_registry.add('compare_dashboard', RFQDashboard);
    return RFQDashboard;
});
