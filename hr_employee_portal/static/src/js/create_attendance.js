odoo.define('hr_employee_portal.attendance_portal', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');

    publicWidget.registry.attendancePortal = publicWidget.Widget.extend({
        selector: '#onchange_create_attendance',
        events: {
            'change #selection_employee_ids': '_onEmployeeChange',
        },

        start: function () {
            var self = this;
            var isEdit = this.$el.find('input[name="attendance_id"]').length > 0;
            
            if (!isEdit) {
                var $employeeSelect = this.$el.find('#selection_employee_ids');
                if ($employeeSelect.children('option').length === 1) {
                    $employeeSelect.val($employeeSelect.children('option').first().val());
                    this._onEmployeeChange();
                }
                
                // Set default check-in to current time
            //     var now = new Date();
            //     var timezoneOffset = now.getTimezoneOffset() * 60000;
            //     var localISOTime = (new Date(now - timezoneOffset)).toISOString().slice(0, 16);
            //     this.$el.find('#check_in_date').val(localISOTime);
            // }
            var now = new Date();
            var timezoneOffset = now.getTimezoneOffset() * 60000;
            var localISOTime = (new Date(now - timezoneOffset)).toISOString().slice(0, 16);
            this.$el.find('#check_in_date').val(localISOTime);
        } else {
            // Set current time for checkout in edit mode
            var now = new Date();
            var timezoneOffset = now.getTimezoneOffset() * 60000;
            var localISOTime = (new Date(now - timezoneOffset)).toISOString().slice(0, 16);
            
            // Only set if checkout field is empty
            if (!this.$el.find('#check_out_date').val()) {
                this.$el.find('#check_out_date').val(localISOTime);
            }
        }
                    
            return this._super.apply(this, arguments);
        },

        _onEmployeeChange: function () {
            var employeeId = this.$el.find('#selection_employee_ids').val();
            if (!employeeId) return;
            
            var self = this;
            ajax.jsonRpc('/hr/employee/get_data', 'call', {
                'employee_id': parseInt(employeeId)
            }).then(function (data) {
                if (data && data.employee_data) {
                    self.$el.find('#job_title').val(data.employee_data.job_title || '');
                    // self.$el.find('#hr_employee_type').val(data.employee_data.hr_employee_type || '');
                    self.$el.find('#hr_employee_type').val(data.employee_data.employee_type_display || '');
                }
            });
        },
    });

    return publicWidget.registry.attendancePortal;
});


// odoo.define('hr_employee_portal.employeeSelectAtt', function (require) {
//     'use strict';

//     var publicWidget = require('web.public.widget');
//     const ajax = require('web.ajax');

//     publicWidget.registry.employeeSelectAtt = publicWidget.Widget.extend({
//         selector: '#onchange_create_attendance',
//         events: {
//             'change #selection_employee_ids': "_onRefresh",
//             'click .send_info_attendance': "_onSubmit",
//         },

//         start: function () {
//             if (this.$("#create_attendance")) {
//                 console.log('In IF');
//                 ajax.jsonRpc('/login/employee/', 'call', {
//                     'method': 'return_login_employee',
//                     'params': { 'attendance': true }
//                 }).then(function (employee_data) {
//                     if (employee_data !== false) {
//                         console.log('employee_data+_+_+_+_', employee_data);
//                         document.querySelector('#selection_employee_ids').value = employee_data['employee_id'];
//                         document.querySelector('#job_title').value = employee_data['job_title'];
//                         document.querySelector('#hr_employee_type').value = employee_data['hr_employee_type'];
//                         if ('task_id' in employee_data) {
//                             document.querySelector('#task').value = employee_data['name'];
//                             document.querySelector('#customer').value = employee_data['partner_id'];
//                             document.querySelector('#location').value = employee_data['partner_location_id'];
//                         }
//                     } else {
//                         document.querySelector('#job_title').value = null;
//                         document.querySelector('#hr_employee_type').value = null;
//                         document.querySelector('#task').value = null;
//                         document.querySelector('#customer').value = null;
//                         document.querySelector('#location').value = null;
//                     }
//                 });
//             }
//             else {
//                 console.log('Going Else');
//             }
//         },

//         _onRefresh: function (ev) {
//             console.log('_onRefresh')
//             if (this.$("#create_attendance")) {
//                 console.log('In IF')
//                 var self = this;
//                 console.log('self+_+_+_+_+_', self);
//                 const employee_id = this.$("#selection_employee_ids").val();
//                 console.log('employee_id+_+_+_+_+_', employee_id, typeof 'employee_id');
//                 ajax.jsonRpc('/employee/data', 'call', {
//                     'method': 'return_employee_data',
//                     'params': { 'employee_id': employee_id, 'attendance': true }
//                 }).then(function (employee_data) {
//                     console.log('employee_data+_+_+_+_', employee_data);
//                     if (employee_data !== false) {
//                         document.querySelector('#job_title').value = employee_data['job_title'];
//                         document.querySelector('#hr_employee_type').value = employee_data['hr_employee_type'];
//                         if ('task_id' in employee_data) {
//                             document.querySelector('#task').value = employee_data['name'];
//                             document.querySelector('#customer').value = employee_data['partner_id'];
//                             document.querySelector('#location').value = employee_data['partner_location_id'];
//                         }
//                     } else {
//                         document.querySelector('#job_title').value = null;
//                         document.querySelector('#hr_employee_type').value = null;
//                         document.querySelector('#task').value = null;
//                         document.querySelector('#customer').value = null;
//                         document.querySelector('#location').value = null;
//                     }
//                 });
//             }
//             else {
//                 console.log('Going Else')
//             }
//         },

//         _onSubmit: function (ev) {
//             console.log('_onSubmit');
//             var emp_id = $("select[id='selection_employee_ids']").val();
//             var check_in_date = document.querySelector('#check_in_date').value;
//             var check_out_date = document.querySelector('#check_out_date').value;
//             var message_error_lives = $("#message_error");
        
//             console.log('emp_id+_+_+_+_', emp_id);
//             console.log('check_in_date+_+_+_+_', check_in_date, typeof check_in_date);
//             console.log('check_out_date+_+_+_+_', check_out_date, typeof check_out_date);
        
//             if (emp_id === '') {
//                 message_error_lives.removeClass('d-none');
//                 message_error_lives.html('Please Select the Employee');
//                 ev.preventDefault();
//             }
//             else if (check_in_date === '') {
//                 message_error_lives.removeClass('d-none');
//                 message_error_lives.html('Please Enter the Check In Date');
//                 ev.preventDefault();
//             }
        
//             if (check_in_date !== '' && check_out_date !== '') {
//                 var splitFrom = check_in_date.split(' - ');
//                 var splitTo = check_out_date.split(' - ');
        
//                 var fromDate = Date.parse(splitFrom[0], splitFrom[1] - 1, splitFrom[2]);
//                 var toDate = Date.parse(splitTo[0], splitTo[1] - 1, splitTo[2]);
        
//                 if (toDate < fromDate) {
//                     message_error_lives.removeClass('d-none');
//                     message_error_lives.html('Please Enter Valid Date. Check Out Date should not be greater than Check In Date.');
//                     ev.preventDefault();
//                 }
//             }
//         },

//         _onSubmit: function (ev) {
//             console.log('_onSubmit');
//             var emp_id = $("select[id='selection_employee_ids']").val();
//             var check_in_date = document.querySelector('#check_in_date').value;
//             var check_out_date = document.querySelector('#check_out_date').value;
//             var message_error_lives = $("#message_error");

//             console.log('emp_id+_+_+_+_', emp_id);
//             console.log('check_in_date+_+_+_+_', check_in_date, typeof check_in_date);
//             console.log('check_out_date+_+_+_+_', check_out_date, typeof check_out_date);

//             if (emp_id === '') {
//                 message_error_lives.removeClass('d-none');
//                 message_error_lives.html('Please Select the Employee');
//                 ev.preventDefault();
//             }
//             else if (check_in_date === '') {
//                 message_error_lives.removeClass('d-none');
//                 message_error_lives.html('Please Enter the Check In Date');
//                 ev.preventDefault();
//             }
//             else if (check_out_date === '') {
//                 message_error_lives.removeClass('d-none');
//                 message_error_lives.html('Please Enter the Check Out Date');
//                 ev.preventDefault();
//             }

//             if (check_in_date !== '' && check_out_date !== '') {

//                 var splitFrom = check_in_date.split(' - ');
//                 var splitTo = check_out_date.split(' - ');

//                 var fromDate = Date.parse(splitFrom[0], splitFrom[1] - 1, splitFrom[2]);
//                 var toDate = Date.parse(splitTo[0], splitTo[1] - 1, splitTo[2]);

//                 if (toDate < fromDate) {
//                     message_error_lives.removeClass('d-none');
//                     message_error_lives.html('Please Enter Valid Date. Check Out Date should not be greater than Check In Date.');
//                     ev.preventDefault();
//                 }
//             }
//         },


//     });
// });
