// odoo.define('hr_employee_portal.employeeSelectDR', function (require) {
//     'use strict';

//     var publicWidget = require('web.public.widget');
//     const ajax = require('web.ajax');

//     Date.prototype.toDateInputValue = (function () {
//         var local = new Date(this);
//         local.setMinutes(this.getMinutes() - this.getTimezoneOffset());
//         return local.toJSON().slice(0, 10);
//     });

//     publicWidget.registry.employeeSelectDR = publicWidget.Widget.extend({
//         selector: '#onchange_create_duty_resumption',
//         events: {
//             'change #selection_employee_ids': "_onRefresh",
//             'change #selection_leave_ids': "_onRefreshLeave",
//             'change #reporting_date': "_onRefreshReportingDate",
//             'click .send_info': "_onSubmit",
//         },

//         start: function () {
//             if (this.$("#create_duty_resumption")) {
//                 console.log('In IF');
//                 document.querySelector('#reporting_date').value = new Date().toDateInputValue();
//                 document.querySelector('#duty_resumption_date').value = new Date().toDateInputValue();
                
//                 // Set current employee as default
//                 ajax.jsonRpc('/login/employee/', 'call', {
//                     'method': 'return_login_employee',
//                     'params': {}
//                 }).then(function (employee_data) {
//                     if (employee_data !== false) {
//                         document.querySelector('#selection_employee_ids').value = employee_data['employee_id'];
//                         document.querySelector('#branch_id').value = employee_data['branch_id'];
//                         document.querySelector('#job_title').value = employee_data['job_title'];
//                         document.querySelector('#selection_manager_ids').value = employee_data['parent_id'];
//                         document.querySelector('#selection_coach_ids').value = employee_data['coach_id'];
                        
//                         // Hide on_behalf_of field initially
//                         document.querySelector('#on_behalf_of_group').classList.add('d-none');
//                     }
//                 });
//             }
//         },

//         _onRefresh: function (ev) {
//             var self = this;
//             const employee_id = this.$("#selection_employee_ids").val();
//             const current_employee_id = this.$el.data('current-employee-id');
            
//             // Show/hide on_behalf_of field based on selection
//             if (employee_id && employee_id != current_employee_id) {
//                 document.querySelector('#on_behalf_of_group').classList.remove('d-none');
//                 document.querySelector('#on_behalf_of').value = employee_id;
//             } else {
//                 document.querySelector('#on_behalf_of_group').classList.add('d-none');
//                 document.querySelector('#on_behalf_of').value = '';
//             }

//             ajax.jsonRpc('/employee/data', 'call', {
//                 'method': 'return_employee_data',
//                 'params': { 'employee_id': employee_id }
//             }).then(function (employee_data) {
//                 if (employee_data !== false) {
//                     document.querySelector('#branch_id').value = employee_data['branch_id'];
//                     document.querySelector('#job_title').value = employee_data['job_title'];
//                     document.querySelector('#selection_manager_ids').value = employee_data['parent_id'];
//                     document.querySelector('#selection_coach_ids').value = employee_data['coach_id'];
                    
//                     // Update the leave types dropdown based on the selected employee
//                     if (employee_data.holidays_status && employee_data.holidays_status.length > 0) {
//                         var holidaysStatusSelect = document.querySelector('#holidays_status_id');
//                         holidaysStatusSelect.innerHTML = '<option value="">Select Time Off Type...</option>';
                        
//                         employee_data.holidays_status.forEach(function(status) {
//                             var option = document.createElement('option');
//                             option.value = status.id;
//                             option.textContent = status.name;
//                             holidaysStatusSelect.appendChild(option);
//                         });
//                     }
                    
//                     // Also update the available leaves dropdown for the selected employee
//                     self._updateLeaveOptions(employee_id);
//                 }
//             });
//         },

//         _updateLeaveOptions: function(employee_id) {
//             ajax.jsonRpc('/employee/leaves', 'call', {
//                 'method': 'return_employee_leaves',
//                 'params': { 'employee_id': employee_id }
//             }).then(function (leaves) {
//                 if (leaves !== false && leaves.length > 0) {
//                     var leaveSelect = document.querySelector('#selection_leave_ids');
//                     leaveSelect.innerHTML = '<option value="">Select Leave...</option>';
                    
//                     leaves.forEach(function(leave) {
//                         var option = document.createElement('option');
//                         option.value = leave.id;
//                         option.textContent = leave.name;
//                         leaveSelect.appendChild(option);
//                     });
//                 } else {
//                     // If no leaves found, clear the dropdown and show a message
//                     var leaveSelect = document.querySelector('#selection_leave_ids');
//                     leaveSelect.innerHTML = '<option value="">No leaves available</option>';
//                 }
//             });
//         },

//         _onRefreshLeave: function (ev) {
//             console.log('_onRefreshLeave')
//             if (this.$("#create_duty_resumption")) {
//                 console.log('In IF')
//                 var self = this;
//                 console.log('self+_+_+_+_+_', self);

//                 const leave_id = this.$("#selection_leave_ids").val();
//                 console.log('leave_id+_+_+_+_+_', leave_id, typeof 'leave_id');

//                 ajax.jsonRpc('/leave/data', 'call', {
//                     'method': 'return_leave_data',
//                     'params': { 'leave_id': leave_id }
//                 }).then(function (leave_type_data) {
//                     console.log('employee_data+_+_+_+_', leave_type_data);
//                     if (leave_type_data !== false) {
//                         document.querySelector('#holidays_status_id').value = leave_type_data;
//                     } else {
//                         document.querySelector('#holidays_status_id').value = null;
//                     }
//                 });
//             }
//             else {
//                 console.log('Going Else')
//             }
//         },

//         _onRefreshReportingDate: function (ev) {
//             console.log('_onRefreshReportingDate');
//             if (this.$("#create_duty_resumption")) {
//                 console.log('In IF')
//                 var self = this;
//                 console.log('self+_+_+_+_+_', self);

//                 const leave_id = this.$("#selection_leave_ids").val();
//                 console.log('leave_id+_+_+_+_+_', leave_id, typeof 'leave_id');

//                 ajax.jsonRpc('/leave/data', 'call', {
//                     'method': 'return_leave_data',
//                     'params': { 'leave_id': leave_id, 'date': true }
//                 }).then(function (to_date) {
//                     console.log('employee_data+_+_+_+_', to_date);
//                     if (to_date !== false && reporting_date !== false) {

//                         var reporting_date = document.querySelector('#reporting_date').value;
//                         var date_to = to_date;

//                         console.log('reporting_date+_+_+_+_', reporting_date)

//                         var splitFrom = reporting_date.split(' - ');
//                         var splitTo = date_to.split(' - ');

//                         var fromDate = Date.parse(splitFrom[0], splitFrom[1] - 1, splitFrom[2]);
//                         var toDate = Date.parse(splitTo[0], splitTo[1] - 1, splitTo[2]);

//                         const diffTime = Math.abs(fromDate - toDate);
//                         const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
//                         console.log(diffTime + " milliseconds");
//                         console.log(diffDays + " days");

//                         if (diffDays > 1) {
//                             document.querySelector('#reason').value = `${diffDays - 1} Days Late`
//                         } else if (diffDays <= 0) {
//                             document.querySelector('#reason').value = `${Math.abs(diffDays) + 1} Days Early`
//                         } else {
//                             document.querySelector('#reason').value = 'On Time'
//                         }

//                     } else {
//                         console.log('Going Else 1')
//                         document.querySelector('#reason').value = ''
//                     }

//                 });
//             }
//             else {
//                 console.log('Going Else 2')
//             }
//         },

//         _onSubmit: function (ev) {
//             console.log('_onSubmit');
//             var emp_id = $("select[id='selection_employee_ids']").val();
//             var leave_id = $("select[id='selection_leave_ids']").val();
//             var reporting_date = document.querySelector('#reporting_date').value;
//             var duty_resumption_date = document.querySelector('#duty_resumption_date').value;
//             var message_error_lives = $("#message_error_lives");

//             console.log('emp_id+_+_+_+_', emp_id);
//             console.log('leave_id+_+_+_+_', leave_id);
//             //       alert('TEST')

//             if (emp_id === '') {
//                 message_error_lives.removeClass('d-none');
//                 message_error_lives.html('Please Select the Employee');
//                 ev.preventDefault();
//             }
//             else if (leave_id === '') {
//                 message_error_lives.removeClass('d-none');
//                 message_error_lives.html('Please Select the Leave');
//                 ev.preventDefault();
//             }
//             else if (reporting_date === '') {
//                 message_error_lives.removeClass('d-none');
//                 message_error_lives.html('Please Select the Reporting Date');
//                 ev.preventDefault();
//             }
//             else if (duty_resumption_date === '') {
//                 message_error_lives.removeClass('d-none');
//                 message_error_lives.html('Please Select the Duty Resumption Date');
//                 ev.preventDefault();
//             }
//         },
//     });
// });


odoo.define('hr_employee_portal.employeeSelectDR', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    const ajax = require('web.ajax');

    Date.prototype.toDateInputValue = (function () {
        var local = new Date(this);
        local.setMinutes(this.getMinutes() - this.getTimezoneOffset());
        return local.toJSON().slice(0, 10);
    });

    publicWidget.registry.employeeSelectDR = publicWidget.Widget.extend({
        selector: '#onchange_create_duty_resumption',
        events: {
            'change #selection_employee_ids': "_onRefresh",
            'change #selection_leave_ids': "_onRefreshLeave",
            'change #reporting_date': "_onRefreshReportingDate",
            'click .send_info': "_onSubmit",
        },

        start: function () {
            if (this.$("#create_duty_resumption")) {
                console.log('In IF');
                document.querySelector('#reporting_date').value = new Date().toDateInputValue();
                document.querySelector('#duty_resumption_date').value = new Date().toDateInputValue();
                
                // Set current employee as default
                ajax.jsonRpc('/login/employee/', 'call', {
                    'method': 'return_login_employee',
                    'params': {}
                }).then(function (employee_data) {
                    if (employee_data !== false) {
                        document.querySelector('#selection_employee_ids').value = employee_data['employee_id'];
                        document.querySelector('#branch_id').value = employee_data['branch_id'];
                        document.querySelector('#job_title').value = employee_data['job_title'];
                        document.querySelector('#selection_manager_ids').value = employee_data['parent_id'];
                        document.querySelector('#selection_coach_ids').value = employee_data['coach_id'];
                        
                        // Hide on_behalf_of field initially
                        document.querySelector('#on_behalf_of_group').classList.add('d-none');
                    }
                });
            }
        },

        _onRefresh: function (ev) {
            var self = this;
            const employee_id = this.$("#selection_employee_ids").val();
            const current_employee_id = this.$el.data('current-employee-id');
            
            // Show/hide on_behalf_of field based on selection
            if (employee_id && employee_id != current_employee_id) {
                document.querySelector('#on_behalf_of_group').classList.remove('d-none');
                document.querySelector('#on_behalf_of').value = employee_id;
                // Enable the on_behalf_of field so its value is sent in the form
                document.querySelector('#on_behalf_of').disabled = false;
            } else {
                document.querySelector('#on_behalf_of_group').classList.add('d-none');
                document.querySelector('#on_behalf_of').value = '';
            }

            ajax.jsonRpc('/employee/data', 'call', {
                'method': 'return_employee_data',
                'params': { 'employee_id': employee_id }
            }).then(function (employee_data) {
                if (employee_data !== false) {
                    document.querySelector('#branch_id').value = employee_data['branch_id'];
                    document.querySelector('#job_title').value = employee_data['job_title'];
                    document.querySelector('#selection_manager_ids').value = employee_data['parent_id'];
                    document.querySelector('#selection_coach_ids').value = employee_data['coach_id'];
                    
                    // Update the leave types dropdown based on the selected employee
                    if (employee_data.holidays_status && employee_data.holidays_status.length > 0) {
                        var holidaysStatusSelect = document.querySelector('#holidays_status_id');
                        holidaysStatusSelect.innerHTML = '<option value="">Select Time Off Type...</option>';
                        
                        employee_data.holidays_status.forEach(function(status) {
                            var option = document.createElement('option');
                            option.value = status.id;
                            option.textContent = status.name;
                            holidaysStatusSelect.appendChild(option);
                        });
                    }
                    
                    // Clear and update the available leaves dropdown for the selected employee
                    self._updateLeaveOptions(employee_id);
                }
            });
        },

        _updateLeaveOptions: function(employee_id) {
            ajax.jsonRpc('/employee/leaves', 'call', {
                'method': 'return_employee_leaves',
                'params': { 'employee_id': employee_id }
            }).then(function (leaves) {
                if (leaves !== false && leaves.length > 0) {
                    var leaveSelect = document.querySelector('#selection_leave_ids');
                    leaveSelect.innerHTML = '<option value="">Select Leave...</option>';
                    
                    leaves.forEach(function(leave) {
                        var option = document.createElement('option');
                        option.value = leave.id;
                        option.textContent = leave.name;
                        leaveSelect.appendChild(option);
                    });
                    
                    // Clear the leave type field when updating the leaves dropdown
                    document.querySelector('#holidays_status_id').value = '';
                } else {
                    // If no leaves found, clear the dropdown and show a message
                    var leaveSelect = document.querySelector('#selection_leave_ids');
                    leaveSelect.innerHTML = '<option value="">No leaves available</option>';
                    
                    // Clear the leave type field when no leaves are available
                    document.querySelector('#holidays_status_id').value = '';
                }
            });
        },

        _onRefreshLeave: function (ev) {
            console.log('_onRefreshLeave')
            if (this.$("#create_duty_resumption")) {
                console.log('In IF')
                var self = this;
                console.log('self+_+_+_+_+_', self);

                const leave_id = this.$("#selection_leave_ids").val();
                console.log('leave_id+_+_+_+_+_', leave_id, typeof 'leave_id');

                if (leave_id) {
                    ajax.jsonRpc('/leave/data', 'call', {
                        'method': 'return_leave_data',
                        'params': { 'leave_id': leave_id }
                    }).then(function (leave_type_data) {
                        console.log('employee_data+_+_+_+_', leave_type_data);
                        if (leave_type_data !== false) {
                            document.querySelector('#holidays_status_id').value = leave_type_data;
                        } else {
                            document.querySelector('#holidays_status_id').value = '';
                        }
                    });
                }
            }
            else {
                console.log('Going Else')
            }
        },

        _onRefreshReportingDate: function (ev) {
            console.log('_onRefreshReportingDate');
            if (this.$("#create_duty_resumption")) {
                console.log('In IF')
                var self = this;
                console.log('self+_+_+_+_+_', self);

                const leave_id = this.$("#selection_leave_ids").val();
                console.log('leave_id+_+_+_+_+_', leave_id, typeof 'leave_id');

                if (leave_id) {
                    ajax.jsonRpc('/leave/data', 'call', {
                        'method': 'return_leave_data',
                        'params': { 'leave_id': leave_id, 'date': true }
                    }).then(function (to_date) {
                        console.log('employee_data+_+_+_+_', to_date);
                        if (to_date !== false) {
                            var reporting_date = document.querySelector('#reporting_date').value;
                            var date_to = to_date;

                            console.log('reporting_date+_+_+_+_', reporting_date)

                            if (reporting_date && date_to) {
                                var splitFrom = reporting_date.split(' - ');
                                var splitTo = date_to.split(' - ');

                                var fromDate = Date.parse(splitFrom[0], splitFrom[1] - 1, splitFrom[2]);
                                var toDate = Date.parse(splitTo[0], splitTo[1] - 1, splitTo[2]);

                                const diffTime = Math.abs(fromDate - toDate);
                                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                                console.log(diffTime + " milliseconds");
                                console.log(diffDays + " days");

                                if (diffDays > 1) {
                                    document.querySelector('#reason').value = `${diffDays - 1} Days Late`;
                                } else if (diffDays <= 0) {
                                    document.querySelector('#reason').value = `${Math.abs(diffDays) + 1} Days Early`;
                                } else {
                                    document.querySelector('#reason').value = 'On Time';
                                }
                            }
                        } else {
                            console.log('Going Else 1')
                            document.querySelector('#reason').value = '';
                        }
                    });
                }
            }
            else {
                console.log('Going Else 2')
            }
        },

        _onSubmit: function (ev) {
            console.log('_onSubmit');
            var emp_id = $("select[id='selection_employee_ids']").val();
            var leave_id = $("select[id='selection_leave_ids']").val();
            var reporting_date = document.querySelector('#reporting_date').value;
            var duty_resumption_date = document.querySelector('#duty_resumption_date').value;
            var message_error_lives = $("#message_error_lives");

            console.log('emp_id+_+_+_+_', emp_id);
            console.log('leave_id+_+_+_+_', leave_id);

            // Enable disabled fields before form submission
            document.querySelector('#holidays_status_id').disabled = false;
            document.querySelector('#branch_id').disabled = false;
            document.querySelector('#job_title').disabled = false;
            document.querySelector('#selection_manager_ids').disabled = false;
            document.querySelector('#selection_coach_ids').disabled = false;

            if (emp_id === '') {
                message_error_lives.removeClass('d-none');
                message_error_lives.html('Please Select the Employee');
                ev.preventDefault();
            }
            else if (leave_id === '') {
                message_error_lives.removeClass('d-none');
                message_error_lives.html('Please Select the Leave');
                ev.preventDefault();
            }
            else if (reporting_date === '') {
                message_error_lives.removeClass('d-none');
                message_error_lives.html('Please Select the Reporting Date');
                ev.preventDefault();
            }
            else if (duty_resumption_date === '') {
                message_error_lives.removeClass('d-none');
                message_error_lives.html('Please Select the Duty Resumption Date');
                ev.preventDefault();
            }
        },
    });
});