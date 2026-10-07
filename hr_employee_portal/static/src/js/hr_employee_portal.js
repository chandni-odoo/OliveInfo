odoo.define('hr_employee_portal.hr_employee_portal', function (require) {
    'use strict';

    require('web.dom_ready');
    var rpc = require('web.rpc');
    $(".holidays_status_half_costome").hide();
    $(".mornig_afternon_type").hide();
    $(".hours_from_to").hide();

    $('#check_in_date').datetimepicker({
        format: 'MM/DD/YYYY HH:mm:ss',
    });
    $('#check_out_date').datetimepicker({
        format: 'MM/DD/YYYY HH:mm:ss'
    });

    // There is no levis_id in XML
    //    $("select[name='levis_id']").on('change', function() {
    //        var holiday_status_id = $(this).find(":selected").val()
    //        rpc.query({
    //            route: "/find/holiday_status_id",
    //            params: {
    //                data: holiday_status_id},
    //            }).then(function (result) {
    //                if (result == 'hour') {
    //                    $(".holidays_status_half_costome").show();
    //                    $("#half_day").prop("checked", true)
    //                    $(".mornig_afternon_type").show();
    //
    //                }
    //                if (result == 'day') {
    //                    $(".holidays_status_half_costome").hide();
    //                    $(".mornig_afternon_type").hide();
    //
    //                }
    //          });
    //    });

    //    $('.shift_type_type').change(function(){
    //        if($('.shift_type_type').val() == 'request_unit_half') {
    //            $(".hours_from_to").hide();
    //            $(".mornig_afternon_type").show();
    //        }
    //        if($('.shift_type_type').val() == 'request_unit_hours') {
    //            $(".mornig_afternon_type").hide();
    //            $(".hours_from_to").show();
    //        }
    //    });

    // Have added the required changes from the below function into the new function of _onSubmit
    // $('.send_info_attendance').on('click', function (ev) {
    //     var check_in_date = $("#check_in_date").val()
    //     var check_out_date = $("#check_out_date").val()
    //     var msg_error = $("#message_error");
    //     var msg_success = $("#message_success");
    //     var msg_form = $('form[name=create_attendance_form]');
    //     var attendance_info = msg_form.serializeArray();
    //     if (check_in_date == "" && check_out_date == "") {
    //         msg_error.removeClass('d-none');
    //         msg_error.html('Please Select Time Off Type');
    //     }
    //     else {
    //         rpc.query({
    //             route: "/add/attendance",
    //             params: {
    //                 data: attendance_info
    //             },
    //         }).then(function (result) {
    //             console.log('$$$$$$$$$$$$$$$$$$$$', result)
    //             if (result.msg) {
    //                 msg_error.removeClass('d-none');
    //                 msg_error.html(result.msg);
    //             }
    //             if (result == true) {
    //                 $('#myModal').modal('hide');
    //             }
    //             return result
    //         });
    //     }
    // });

    // Have added the required changes from the below function into the new function of _onSubmit
    //	$('.send_info').on('click', function (ev) {
    //        var leave_id = $("select[name='holidays_status_ids']").val()
    ////        var start_date_leave = $("select[name='start_date_leave']").val()
    ////        var end_date_leave = $("select[name='end_date_leave']").val()
    ////        var description_leave = $("select[name='description_leave']").val()
    //        var message_error_lives = $("#message_error_lives");
    ////        var message_success_lives = $("#message_success_lives");
    ////        var msg_form = $('form[name=create_time_off]');
    ////        var mytime_ofoo_info = msg_form.serializeArray();
    //
    //        console.log('mytime_ofoo_info+_+_+_', mytime_ofoo_info)
    //        console.log('leave_id+_+_+_+_', leave_id)
    //        alert('Leave ID')
    //
    //        if(leave_id == ""){
    //            message_error_lives.removeClass('d-none');
    //            message_error_lives.html('Please Select Time Off Type');
    //        }
    //        else{
    //        //        alert('check')
    //            rpc.query({
    //            route: "/add/mytimeoff",
    //            params: {
    //                data: mytime_ofoo_info},
    //            }).then(function (result) {
    //                console.log('$$$$$$$$$$$$$$$$$$$$', result)
    //            	if (result.msg) {
    //            		message_error_lives.removeClass('d-none');
    //            		message_error_lives.html(result.msg);
    //	            }
    //	            if (result == true){
    //	            	$('#myLeaves').modal('hide');
    //	            }
    //            return result
    //          });
    //        }
    //    });
});