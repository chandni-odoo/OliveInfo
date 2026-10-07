odoo.define('pways_record_approval.form_view', function (require) {
"use strict";
    var core = require('web.core');
    var FormRenderer = require('web.FormRenderer');
    var rpc = require('web.rpc');
    var _t = core._t;

    FormRenderer.include({
        _renderTagHeader: function(node) {
            var self = this;
            var $statusbar = this._super(node);
            var def = this._rpc({
                model: 'record.approval',
                method: 'get_approval',
                args: [this.state.model, this.state.res_id],
            });
            def.then(function(result) {

                var buttons = $statusbar.find(".o_statusbar_buttons");
                var for_hide = ['pways_action_approve', 'pways_action_reject', 'pways_action_pending', 'pways_action_send_approval']
                var approval = ['pways_action_approve', 'pways_action_reject', 'pways_action_pending']
                if (!result['show_approval'] && !result['show_all']) {
                    // ----------Hide All buttons------------
                    _.each(buttons.children(), function(button) {
                        $(button).css({ display: 'none' });
                    });
                } else if (result['show_approval']) {
                    //----------Hide Other buttons------------
                    _.each(buttons.children(), function(button) {
                        if (!approval.includes($(button).attr("name"))) {
                            $(button).css({ display: 'none' });
                        }
                    });
                } else if (result['show_all']) {
                    //----------Hide approval buttons---------
                    _.each(buttons.children(), function(button) {
                        if (for_hide.includes($(button).attr("name"))) {
                            $(button).css({ display: 'none' });
                        }
                    });
                }
                if (!result['show_all'] && !result['to_approve']) {
                    //----------Show approval status wizard---------
                    _.each(buttons.children(), function(button) {
                        if ($(button).attr("name") === 'pways_action_pending') {
                            $(button).css("display", "");
                        }
                    });
                }
                if (result['to_approve']) {
                    _.each(buttons.children(), function(button) {
                        if ($(button).attr("name") === 'pways_action_send_approval') {
                            $(button).css("display", "");
                        }
                    });
                }

            });
            return $statusbar;
        },

        _renderHeaderButtons: function(node) {
            var is_approve = false;
            var is_reject = false;
            var is_pending = false;
            var for_approve = false;
            console.log("________2323232323")
            _.each(node.children, function(child) {
                if (child.attrs.name === 'pways_action_approve') {
                    is_approve = true;
                }
                if (child.attrs.name === 'pways_action_reject') {
                    is_reject = true;
                }
                if (child.attrs.name === 'pways_action_pending') {
                    is_pending = true;
                }
                if (child.attrs.name === 'pways_action_send_approval') {
                    for_approve = true;
                }
            });
            if (!is_approve) {
                node.children.push({
                    tag: "button",
                    attrs: {
                        name: "pways_action_approve",
                        type: "object",
                        string: "Approve",
                        class: "btn-primary",
                    }
                });
            }
            if (!for_approve) {
                node.children.push({
                    tag: "button",
                    attrs: {
                        name: "pways_action_send_approval",
                        type: "object",
                        string: "Send For Approval",
                        class: "btn-primary",
                    }
                });
            }
            if (!is_reject) {
                node.children.push({
                    tag: "button",
                    attrs: {
                        name: "pways_action_reject",
                        type: "object",
                        string: "Reject",
                    }
                });
            }
            if (!is_reject) {
                node.children.push({
                    tag: "button",
                    attrs: {
                        name: "pways_action_pending",
                        type: "object",
                        string: "Approval Status",
                    }
                });
            }
            return this._super.apply(this, arguments);
        },
    });
});