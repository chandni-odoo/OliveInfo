odoo.define('hr_employee_portal.employeeSelect', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    const ajax = require('web.ajax');

    publicWidget.registry.employeeSelect2 = publicWidget.Widget.extend({
        selector: '#onchange_emp_new',
        events: {
            'change #selection_employee_ids': "_onChangeEmployee",
            'change .duration': "_onChangeDuration",
            'click .send_info': "_onSubmit",
        },

        _formatDate: function(dateStr) {
            if (!dateStr) return '';
            const parts = dateStr.split('-');
            if (parts.length === 3) {
                return `${parts[2]}/${parts[1]}/${parts[0]}`;
            }
            return dateStr; 
        },

        start: function () {
            if (this.$("#create_leave_page_js")) {
                console.log('In IF');
                ajax.jsonRpc('/login/employee/', 'call', {
                    'method': 'return_login_employee',
                    'params': {}
                }).then(function (employee_data) {
                    if (employee_data !== false) {
                        document.querySelector('#selection_employee_ids').value = employee_data['employee_id'];
                        
                        if (document.querySelector('#branch_id')) {
                            document.querySelector('#branch_id').value = employee_data['branch_id'];
                        }
                        if (document.querySelector('#job_title')) {
                            document.querySelector('#job_title').value = employee_data['job_title'];
                        }
                        if (document.querySelector('#selection_manager_ids')) {
                            document.querySelector('#selection_manager_ids').value = employee_data['parent_id'];
                        }
                        if (document.querySelector('#selection_coach_ids')) {
                            document.querySelector('#selection_coach_ids').value = employee_data['coach_id'];
                        }
                        if (document.querySelector('#joining_date')) {
                            document.querySelector('#joining_date').value = this._formatDate(employee_data['joining_date']);
                        }
                        if (document.querySelector('#company_id')) {
                            document.querySelector('#company_id').value = employee_data['company_id'];
                        }
                        if (document.querySelector('#rem_leaves')) {
                            if ('virtual_remaining_leaves' in employee_data) {
                                document.querySelector('#rem_leaves').value = employee_data['virtual_remaining_leaves'];
                            } else {
                                document.querySelector('#rem_leaves').value = null;
                            }
                        }
                        
                        // Hide the on behalf container by default for login employee
                        if (document.querySelector('#on_behalf_container')) {
                            document.querySelector('#on_behalf_container').classList.add('d-none');
                        }
                    } else {
                        this._clearFormFields();
                    }
                }.bind(this)); 
            }
        },

        _clearFormFields: function() {
            const fields = ['#selection_employee_ids', '#branch_id', '#job_title', '#selection_manager_ids', 
                           '#selection_coach_ids', '#joining_date', '#company_id', '#rem_leaves'];
            
            fields.forEach(field => {
                const element = document.querySelector(field);
                if (element) {
                    element.value = null;
                }
            });
            
            // Hide on behalf container
            if (document.querySelector('#on_behalf_container')) {
                document.querySelector('#on_behalf_container').classList.add('d-none');
            }
        },

        _onChangeEmployee: function (ev) {
            console.log('_onChangeEmployee called');
            if (this.$("#create_leave_page_js")) {
                console.log('In IF');
                var self = this;
                const employee_id = this.$("#selection_employee_ids").val();
                const currentEmployeeId = document.querySelector('#current_employee_id').value;
                
                if (!employee_id) {
                    this._clearFormFields();
                    return;
                }
                
                console.log('employee_id selected:', employee_id);
                
                ajax.jsonRpc('/employee/data', 'call', {
                    'method': 'return_employee_data',
                    'params': { 'employee_id': employee_id }
                }).then(function (employee_data) {
                    console.log('employee_data received:', employee_data);
                    
                    if (employee_data !== false) {
                        // Update standard employee fields
                        // (existing code for updating fields)
                        if (document.querySelector('#branch_id')) {
                            document.querySelector('#branch_id').value = employee_data['branch_id'];
                        }
                        if (document.querySelector('#job_title')) {
                            document.querySelector('#job_title').value = employee_data['job_title'];
                        }
                        if (document.querySelector('#selection_manager_ids')) {
                            document.querySelector('#selection_manager_ids').value = employee_data['parent_id'];
                        }
                        if (document.querySelector('#selection_coach_ids')) {
                            document.querySelector('#selection_coach_ids').value = employee_data['coach_id'];
                        }
                        if (document.querySelector('#joining_date')) {
                            document.querySelector('#joining_date').value = self._formatDate(employee_data['joining_date']);
                        }
                        if (document.querySelector('#company_id')) {
                            document.querySelector('#company_id').value = employee_data['company_id'];
                        }
                        if (document.querySelector('#rem_leaves')) {
                            if ('virtual_remaining_leaves' in employee_data) {
                                document.querySelector('#rem_leaves').value = employee_data['virtual_remaining_leaves'];
                            } else {
                                document.querySelector('#rem_leaves').value = null;
                            }
                        }
                        
                        // Update time off types based on selected employee
                        if (employee_data['holidays_status'] && document.querySelector('#holidays_status_ids')) {
                            const selectElement = document.querySelector('#holidays_status_ids');
                            // Clear existing options
                            selectElement.innerHTML = '<option value="">Time Off Type...</option>';
                            
                            // Add new options based on employee's available leave types
                            employee_data['holidays_status'].forEach(function(status) {
                                const option = document.createElement('option');
                                option.value = status.id;
                                option.textContent = status.name;
                                selectElement.appendChild(option);
                            });
                        }
                     
                        // Handle "On Behalf" field behavior
                        const onBehalfContainer = document.querySelector('#on_behalf_container');
                        const onBehalfSelect = document.querySelector('#on_behalf_of');
                        
                        if (onBehalfContainer && onBehalfSelect) {
                            // Check if selected employee is the current logged-in employee
                            const isCurrentEmployee = (employee_id == currentEmployeeId);
                            
                            if (isCurrentEmployee) {
                                // If current employee is selected, hide the "On Behalf Of" field
                                onBehalfContainer.classList.add('d-none');
                                onBehalfSelect.value = '';
                            } else {
                                // If another employee is selected, show the field and set its value
                                onBehalfContainer.classList.remove('d-none');
                                
                                // Find the option for this employee and select it
                                const options = onBehalfSelect.options;
                                let found = false;
                                
                                for (let i = 0; i < options.length; i++) {
                                    if (options[i].value == employee_id) {
                                        onBehalfSelect.value = employee_id;
                                        found = true;
                                        break;
                                    }
                                }
                                
                                // If no option exists for this employee, we need to add one
                                if (!found && employee_data.employee_name) {
                                    const newOption = document.createElement('option');
                                    newOption.value = employee_id;
                                    newOption.textContent = employee_data.employee_name;
                                    onBehalfSelect.appendChild(newOption);
                                    onBehalfSelect.value = employee_id;
                                }
                            }
                        }
                    } else {
                        self._clearFormFields();
                    }
                });
            }
        },

        _onChangeDuration: function (ev) {
            console.log('_onChangeDuration');
            var start_date = document.querySelector('#start_date').value;
            var end_date = document.querySelector('#end_date').value;

            if (start_date !== '' && end_date !== '') {
                var splitFrom = start_date.split(' - ');
                var splitTo = end_date.split(' - ');

                var fromDate = Date.parse(splitFrom[0], splitFrom[1] - 1, splitFrom[2]);
                var toDate = Date.parse(splitTo[0], splitTo[1] - 1, splitTo[2]);

                if (toDate > fromDate) {
                    const diffTime = Math.abs(fromDate - toDate);
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                    console.log(diffDays + " days");
                    document.querySelector('#duration').value = `${diffDays}`;
                }
            }
        },

        _onSubmit: function (ev) {
            console.log('_onSubmit');
            var emp_id = $("select[id='selection_employee_ids']").val();
            var leave_id = $("select[name='holidays_status_ids']").val();
            var start_date = document.querySelector('#start_date').value;
            var end_date = document.querySelector('#end_date').value;
            var message_error_lives = $("#message_error_lives");

            console.log('emp_id+_+_+_+_', emp_id);
            console.log('leave_id+_+_+_+_', leave_id);
            console.log('start_date+_+_+_+_', start_date, typeof start_date);
            console.log('end_date+_+_+_+_', end_date, typeof end_date);

            if (emp_id === '') {
                message_error_lives.removeClass('d-none');
                message_error_lives.html('Please Select the Employee');
                ev.preventDefault();
            }
            else if (leave_id === '') {
                message_error_lives.removeClass('d-none');
                message_error_lives.html('Please Select the Time Off Type');
                ev.preventDefault();
            }
            else if (start_date === '') {
                message_error_lives.removeClass('d-none');
                message_error_lives.html('Please Select the Start Date');
                ev.preventDefault();
            }
            else if (end_date === '') {
                message_error_lives.removeClass('d-none');
                message_error_lives.html('Please Select the End Date');
                ev.preventDefault();
            }

            if (start_date !== '' && end_date !== '') {
                var splitFrom = start_date.split(' - ');
                var splitTo = end_date.split(' - ');

                var fromDate = Date.parse(splitFrom[0], splitFrom[1] - 1, splitFrom[2]);
                var toDate = Date.parse(splitTo[0], splitTo[1] - 1, splitTo[2]);

                if (toDate < fromDate) {
                    message_error_lives.removeClass('d-none');
                    message_error_lives.html('Please Enter Valid Date. End Date should not be greater than Start Date.');
                    ev.preventDefault();
                }
            }
        },

    });
});