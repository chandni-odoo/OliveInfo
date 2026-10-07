odoo.define('hr_expense_portal.hr_expense_portal', function (require) {
'use strict';

	require('web.dom_ready');
	var rpc = require('web.rpc');

    $('.send_info_expense').on('click', function (ev) {
        var msg_form = $('form[name=create_expense_form]');
        var request_info = msg_form.serializeArray();
        rpc.query({
            route: "/add/expense",
            params: {
                data: request_info},
            }).then(function (result) {
                if (result.msg) {
                    msg_error.removeClass('d-none');
                    console.log('$$$$$$$$$$$$$$$$$$$$', result.msg)
                    msg_error.html(result.msg);
                }
                if (result == true){
                    $('#my_expense').modal('hide');
                }
            return result
          });
        
    });
});