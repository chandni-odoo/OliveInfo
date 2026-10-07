odoo.define('hr_payroll_extended.Dashboard', function (require) {
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

var PayslipDashboard = AbstractAction.extend({
    template: 'PayslipDashboard',
    events: {
        'keyup .searchInput': '_onKeypress',
    },
    
    init: function(parent, options) {
        this._super(parent, options);
        this.reqisition_id = options.context.reqisition_id;
        this.employee_ids = [];
        this.header = [];
        if (!this.reqisition_id)
        {
            this.reqisition_id = parseInt(utils.get_cookie('id'));
        }
    },
    fetch_data: function () {
        var self = this;
        var def1 =  this._rpc({
            model: 'pre.payroll.dashboard',
            method: 'get_payslip_line_data',
            args: [this.reqisition_id],
        }).then(function(result) {
            self.employee_ids = result;
            self.header = self.employee_ids.header[0];
        });
        return $.when(def1);
    },
    willStart: function() {
        var self = this;
        return $.when(ajax.loadLibs(this), this._super()).then(function() {
            return self.fetch_data();
        });
    },
    start: function() {
        utils.set_cookie("id", this.reqisition_id);
        var self = this;
        return this._super().then(function() {
            self.render_dashboards(self.employee_ids, self.employee_ids.employee_ids, self.header);
        });
    },
    _onKeypress: function (ev) {
        var search_text = (this.$('.searchInput').val()).toLowerCase();
        var res = this.employee_ids;
        var header = this.header;
        var employee_ids = []
        _.each(this.employee_ids.employee_ids, function (emp) {
            if ((emp.employee.toLowerCase()).indexOf(search_text) != -1) {
                employee_ids.push(emp)
            }
            if ((emp.emp_code.toLowerCase()).indexOf(search_text) != -1) {
                employee_ids.push(emp)
            }
        });
        this.render_dashboards(res, employee_ids, header, search_text);
    },
    render_dashboards: function (res, employee_ids, header, search=null) {
        this.$('.o_employee_dashboard').html(QWeb.render('EmpPayslip', 
            {
                widget: res, 
                'employee_ids': employee_ids,
                'header': header,
                'search_text': search,
            }));
        var value = $("#o-export-search-filter").val();
        $("#o-export-search-filter").focus().val('').val(value);
    }
});

core.action_registry.add('payslip_dashboard', PayslipDashboard);

return PayslipDashboard;

});

