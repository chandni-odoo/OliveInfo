odoo.define('mtech_vehicle_extended.OperationDashboard', function (require) {
    "use strict";
    
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var _t = core._t;
    var QWeb = core.qweb;
    var ajax = require('web.ajax');
    var rpc = require('web.rpc');

    var OperationDashboard = AbstractAction.extend({
        template: 'OperationDashboard',
        init: function () {
            /**
            * Initializes an object with a list of dashboard template names.
            *
            * @returns {undefined}
            */
            this._super.apply(this, arguments);
            this.dashboard_templates = ['DashboardMain'];
        },

        start: function () {
            var self = this;
            this.set("title", 'OperationDashboard');
            return this._super().then(function() {
                self.render_dashboards();
                // self.render_graphs();
            });
        },
        render_dashboards: function() {
            /**
            * Renders the dashboards for the OperationDashboard.
            *
            * @function
            * @memberof OperationDashboard
            * @returns {void}
            */
            var self = this;
            _.each(this.dashboard_templates, function(template) {
                    self.$el.find('.o_operation_schedule_dashboard').append(QWeb.render(template, {widget: self}));
            });
        },
    });

    core.action_registry.add('operation_dashboard', OperationDashboard);
    return OperationDashboard;
});
