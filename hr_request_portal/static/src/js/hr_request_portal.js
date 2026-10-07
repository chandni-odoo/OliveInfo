// odoo.define('hr_request_portal.hr_request_portal', function (require) {
//     'use strict';
    
//     require('web.dom_ready');
//     var rpc = require('web.rpc');
//     var core = require('web.core');
//     var _t = core._t;
//     var csrf_token = core.csrf_token;
    
//     $(document).ready(function() {
//         // Initially hide the relieving date field
//         $('#relieving_date_container').hide();
        
//         // Handle request type change
//         $('select[name="request_selection"]').on('change', function() {
//             var selectedOption = $('option:selected', this);
//             var selectedText = selectedOption.text().trim().toLowerCase();
            
//             if (selectedText.includes('termination') || selectedText.includes('resignation')) {
//                 $('#relieving_date_container').show();
//             } else {
//                 $('#relieving_date_container').hide();
//                 $('input[name="relieving_date"]').val('');
//             }
//         }).trigger('change');
        
//         // Handle form submission
//         $('.send_info_request').on('click', function(ev) {
//             ev.preventDefault();
//             ev.stopPropagation();
            
//             var $form = $('form[name=create_request_form]');
//             var $errorDiv = $("#request_error");
//             var $submitBtn = $(this);
            
//             // Clear previous errors
//             $errorDiv.addClass('d-none').html('');
            
//             // Disable button to prevent double submission
//             $submitBtn.prop('disabled', true);
            
//             // Prepare form data
//             var formData = $form.serializeArray();
            
//             // Add CSRF token to form data
//             formData.push({name: 'csrf_token', value: csrf_token});
            
//             // Add file data if needed
//             var fileInputs = $form.find('input[type="file"]');
//             if (fileInputs.length) {
//                 var formDataObj = new FormData();
//                 $.each(formData, function(i, field) {
//                     formDataObj.append(field.name, field.value);
//                 });
                
//                 // Add files
//                 fileInputs.each(function() {
//                     if (this.files && this.files[0]) {
//                         formDataObj.append(this.name, this.files[0]);
//                     }
//                 });
                
//                 // Send with FormData
//                 $.ajax({
//                     url: '/add/request',
//                     type: 'POST',
//                     data: formDataObj,
//                     processData: false,
//                     contentType: false,
//                     success: function(result) {
//                         handleSubmissionResponse(result);
//                     },
//                     error: function(xhr) {
//                         handleSubmissionError(xhr);
//                     },
//                     complete: function() {
//                         $submitBtn.prop('disabled', false);
//                     }
//                 });
//             } else {
//                 // Send without files
//                 rpc.query({
//                     route: '/add/request',
//                     params: {data: formData},
//                 }).then(function(result) {
//                     handleSubmissionResponse(result);
//                 }).catch(function(error) {
//                     handleSubmissionError(error);
//                 }).finally(function() {
//                     $submitBtn.prop('disabled', false);
//                 });
//             }
            
//             function handleSubmissionResponse(result) {
//                 if (result.success) {
//                     $('#myrequest').modal('hide');
//                     // Clear form
//                     $form[0].reset();
//                     // Redirect to requests list
//                     window.location.href = result.redirect_url || '/my/request';
//                 } else {
//                     $errorDiv.removeClass('d-none').html(result.msg || _t('An error occurred'));
//                 }
//             }
            
//             function handleSubmissionError(error) {
//                 var errorMsg = _t('Request failed. Please try again.');
//                 if (error.responseJSON && error.responseJSON.error) {
//                     errorMsg = error.responseJSON.error;
//                 }
//                 $errorDiv.removeClass('d-none').html(errorMsg);
//             }
//         });
        
//         // Fetch employee info on page load if needed
//         var employeeNameField = $('#employee_name_field');
//         if (!employeeNameField.val() || !employeeNameField.val().trim()) {
//             rpc.query({
//                 route: '/my/employee_info',
//                 params: {},
//             }).then(function(result) {
//                 if (result && result.employee_name) {
//                     employeeNameField.val(result.employee_name);
//                 }
//             });
//         }
//     });
// });


odoo.define('hr_request_portal.hr_request_portal', function (require) {
    'use strict';
    
    require('web.dom_ready');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;
    var csrf_token = core.csrf_token;
    
    $(document).ready(function() {
        // Initialize field visibility
        $('#relieving_date_container').hide();
        $('#reason_for_leaving_container').hide();
        $('#notice_period_container').hide();
        
        // Request type change handler
        $('select[name="request_selection"]').on('change', function() {
            var selectedText = $(this).find('option:selected').text().toLowerCase();
            var isResignation = selectedText.includes('resignation') || selectedText.includes('termination');
            
            // Toggle field visibility
            $('#relieving_date_container').toggle(isResignation);
            $('#reason_for_leaving_container').toggle(isResignation);
            $('#resignation_date_container').toggle(isResignation);
            $('#notice_period_container').toggle(isResignation);
            $('input[name="languages"]').closest('.form-group').toggle(!isResignation);
            
            // Reset fields when hidden
            if (!isResignation) {
                $('input[name="relieving_date"]').val('');
                $('select[name="reason_for_leaving_id"]').val('');
                $('input[name="resignation_date"]').val('');
            }
        }).trigger('change');

        // Employee change handler
        $('select[name="on_behalf_of"]').on('change', function() {
            var employeeId = $(this).val();
            if (employeeId) {
                rpc.query({
                    route: '/get/employee/notice_period',
                    params: {employee_id: employeeId},
                }).then(function(result) {
                    $('#notice_period_field').text(result.notice_period || 'Not specified');
                });
            }
        });
        
        // The rest of the code stays the same
        $('.send_info_request').on('click', function(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            
            var $form = $('form[name=create_request_form]');
            var $errorDiv = $("#request_error");
            var $submitBtn = $(this);
            
            // Clear previous errors
            $errorDiv.addClass('d-none').html('');
            
            // Disable button to prevent double submission
            $submitBtn.prop('disabled', true);
            
            // Prepare form data
            var formData = $form.serializeArray();
            
            // Add CSRF token to form data
            formData.push({name: 'csrf_token', value: csrf_token});
            
            // Add file data if needed
            var fileInputs = $form.find('input[type="file"]');
            if (fileInputs.length) {
                var formDataObj = new FormData();
                $.each(formData, function(i, field) {
                    formDataObj.append(field.name, field.value);
                });
                
                // Add files
                fileInputs.each(function() {
                    if (this.files && this.files[0]) {
                        formDataObj.append(this.name, this.files[0]);
                    }
                });
                
                // Send with FormData
                $.ajax({
                    url: '/add/request',
                    type: 'POST',
                    data: formDataObj,
                    processData: false,
                    contentType: false,
                    success: function(result) {
                        handleSubmissionResponse(result);
                    },
                    error: function(xhr) {
                        handleSubmissionError(xhr);
                    },
                    complete: function() {
                        $submitBtn.prop('disabled', false);
                    }
                });
            } else {
                // Send without files
                rpc.query({
                    route: '/add/request',
                    params: {data: formData},
                }).then(function(result) {
                    handleSubmissionResponse(result);
                }).catch(function(error) {
                    handleSubmissionError(error);
                }).finally(function() {
                    $submitBtn.prop('disabled', false);
                });
            }
            
            function handleSubmissionResponse(result) {
                if (result.success) {
                    $('#myrequest').modal('hide');
                    // Clear form
                    $form[0].reset();
                    // Redirect to requests list
                    window.location.href = result.redirect_url || '/my/request';
                } else {
                    $errorDiv.removeClass('d-none').html(result.msg || _t('An error occurred'));
                }
            }
            
            function handleSubmissionError(error) {
                var errorMsg = _t('Request failed. Please try again.');
                if (error.responseJSON && error.responseJSON.error) {
                    errorMsg = error.responseJSON.error;
                }
                $errorDiv.removeClass('d-none').html(errorMsg);
            }
        });
        
        // Fetch employee info on page load if needed
        var employeeNameField = $('#employee_name_field');
        if (!employeeNameField.val() || !employeeNameField.val().trim()) {
            rpc.query({
                route: '/my/employee_info',
                params: {},
            }).then(function(result) {
                if (result && result.employee_name) {
                    employeeNameField.val(result.employee_name);
                }
            });
        }
    });
});