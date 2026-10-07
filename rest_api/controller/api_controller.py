import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import http
from odoo.http import request, Response
import json
import base64
from datetime import datetime, time

from odoo.http import root
from datetime import datetime

from odoo import models, fields, api
from datetime import timedelta
import ast
import secrets


class MyAPIController(http.Controller):

    @http.route('/api/login', type='json', auth='public', methods=['POST'], csrf=False)
    def validate_employee_login(self, **kwargs):
        request_data = json.loads(request.httprequest.data.decode('utf-8'))

        pin = request_data.get('pin')
        imei_number = request_data.get('unique_id')
        company_name = request_data.get('company')

        if not pin or not imei_number or not company_name:
            return {'error': 'PIN, imei_number, and company are required'}

        employee = request.env['hr.employee'].sudo().search([
            ('pin', '=', pin),
            ('imei_number', '=', imei_number),
            ('company_id.name', '=', company_name),
        ], limit=1)
        print('employee++++++++++++++', employee)

        if not employee:
            return {'error': 'Invalid login credentials'}

        session_token = secrets.token_hex(32)
        expiration = fields.Datetime.now() + timedelta(days=1)

        # existing_token = request.env['employee.api.token'].sudo().search([
        #     ('employee_id', '=', employee.id)
        # ], limit=1)

        request.env['employee.api.token'].sudo().create({
            'employee_id': employee.id,
            'token': session_token,
            'expiration_date': expiration
        })

        return_vals = {
            'status': 'success',
            'employee_id': employee.id,
            'employee_name': employee.name,
        }

        helpers = []

        # Check Operation Scheduled
        operation = request.env['operation.schedule'].sudo().search(
            [('employee_id', '=', employee.id), ('scheduled_date', '=', fields.datetime.today()),
             ('active_shift', '=', True)])
        print('operation+++++++++++++++++++', operation)
        if operation:
            operation = operation[0]
            print('operation++++++++++++++++', operation)
            helper_operation = request.env['operation.schedule'].sudo().search(
                [('scheduled_date', '=', fields.datetime.today()), ('vehicle_id', '=', operation.vehicle_id.id),
                 ('shift_type', '=', operation.shift_type.id), ('employee_id', '!=', employee.id)])
            print('helper_operation+++++++++++++++++++++', helper_operation)
            for helper in helper_operation:
                helpers.append({
                    'id': helper.employee_id.id,
                    'name': helper.employee_id.name,
                })
        return_vals.update({
            'helpers': helpers,
            'shift_id': operation.shift_type.id if operation else False,
            'shift_name': operation.shift_type.name if operation else False,
            'vehicle_id': operation.vehicle_id.id if operation else False,
            'vehicle_name': operation.vehicle_id.name if operation else False,
            'message': "Login successful.",
            'session_token': session_token,
            'expiry_time': fields.Datetime.to_string(expiration),
        })

        return return_vals

    @http.route('/api/logout', type='json', auth='public', methods=['POST'], csrf=False)
    def validate_employee_logout(self, **kwargs):
        token = request.httprequest.headers.get('Authorization')
        token = token.replace("Bearer ", "")

        if not token:
            return {'error': 'Authorization token is missing'}

        existing_token = request.env['employee.api.token'].sudo().search([
            ('token', '=', token)
        ], limit=1)

        if existing_token:
            existing_token.sudo().unlink()
            return {'message': 'Logout successful'}
        else:
            return {'error': 'Invalid or expired token'}

    @http.route('/api/skips', type='json', auth='public', methods=['POST'], csrf=False)
    def send_skip_apis(self, **kwargs):

        token = request.httprequest.headers.get('Authorization')
        token_record = self.validate_token(token)
        if not token_record:
            return {
                "status": "Fail",
                "message": "Invalid Token.",
            }

        return_result = {
            "status": "success",
            "message": "Skips Data retrieved successfully.",
        }

        data_list = []

        maintenance_ids = request.env['maintenance.equipment'].with_context(lang='en_GB').sudo().search([])

        for maintenance in maintenance_ids:
            if maintenance.category_id.name == 'Skip':
                data_list.append({
                    'id': maintenance.id,
                    'name': maintenance.name,
                    'customer': maintenance.customer_id.name if maintenance.customer_id else False,
                    'task': maintenance.task_id.name if maintenance.task_id else False,
                    # 'skips_type': maintenance.category_id.name if maintenance.category_id else False,
                    'skips_type': maintenance.equipment_type_id.name if maintenance.equipment_type_id else False,
                    'status': maintenance.status,
                })

        return_result.update({
            'data': data_list
        })

        return return_result

        # return request.make_response(json.dumps({
        #     'message': 'Employee created successfully',
        #     'id': employee.id,
        #     'name': employee.name,
        #     'email': employee.work_email
        # }), headers=[('Content-Type', 'application/json')])

    @http.route('/api/land_fil', type='json', auth='public', methods=['POST'], csrf=False)
    def send_land_fil_apis(self, **kwargs):

        token = request.httprequest.headers.get('Authorization')
        token_record = self.validate_token(token)
        if not token_record:
            return {
                "status": "Fail",
                "message": "Invalid Token.",
            }

        return_result = {
            "status": "success",
            "message": "Land Fill Data retrieved successfully.",
        }

        data_list = []

        fleet_ids = request.env['fleet.landfill'].sudo().search([])

        for fleet in fleet_ids:
            data_list.append({
                'id': fleet.id,
                'name': fleet.name,
            })

        return_result.update({
            'data': data_list
        })

        return return_result

    # -------------------------------------------------------------------

    @http.route('/api/secure-data', type='json', auth='public', methods=['POST'], csrf=False)
    def send_secure_api_apis(self, **kwargs):

        token = request.httprequest.headers.get('Authorization')
        token_record = self.validate_token(token)
        if not token_record:
            return {
                "status": "Fail",
                "message": "Invalid Token.",
            }

        request_data = json.loads(request.httprequest.data.decode('utf-8'))

        current_date_str = request_data.get('current_date')
        vehicle_id = request_data.get('vehicle_id')
        shift_id = request_data.get('shift_id')

        print('current_date++++++++++++++++', current_date_str, type(current_date_str))
        print('vehicle_id++++++++++++++++', vehicle_id)
        print('shift_id++++++++++++++++', shift_id)

        if not current_date_str or not vehicle_id or not shift_id:
            return {'error': 'Current Date, Vehicle Id, and Shift Id are required'}

        try:
            current_date = datetime.strptime(current_date_str, '%Y-%m-%d').date()
        except ValueError:
            return {'error': 'Invalid date format, expected YYYY-MM-DD'}

        return_result = {
            "status": "success",
            "message": "Data retrieved successfully.",
        }
        data_list = []

        print('current_date+++++++++++++++++', current_date)
        start_datetime = datetime.combine(current_date, time(0, 0, 0))
        end_datetime = datetime.combine(current_date, time(23, 59, 59))

        trip_sheet = request.env['custom.trip.sheet'].sudo().search([
            ('schedule_date', '>=', start_datetime),
            ('schedule_date', '<=', end_datetime),
            ('vehicle_no_id', '=', int(vehicle_id)),
            ('shift_id', '=', int(shift_id)),
        ])

        if trip_sheet:
            for trip in trip_sheet:

                helper_list = []
                for helper in trip.helper_ids:
                    helper_list.append({
                        'id': helper.id,
                        'name': helper.name,
                    })

                alternate_skip_list = []
                for alternate in trip.task_id.alternate_skip_types_ids:
                    alternate_skip_list.append({
                        'id': alternate.id,
                        'name': alternate.name,
                    })

                location = str(trip.task_id.seq_code) + ' ' + str(trip.task_id.name) + ' ' + str(
                    trip.task_id.partner_location_id.name)

                qatar_time = trip.schedule_date + timedelta(hours=3)

                vals = {
                    "id": trip.id,
                    "name": trip.req_seq,
                    "company_id": request.env.company.id,
                    "company_name": request.env.company.name,
                    "hold_do": trip.task_id.sale_order_id.is_hold,  # need to discuss new code from sale
                    "hold_reason": trip.task_id.sale_order_id.hold_reason,  # need to discuss new code sale
                    "task_latitude": trip.task_id.latitude,  # from task
                    "task_longitude": trip.task_id.longitude,  # from task
                    "task_description": trip.task_id.description,
                    "service_only": False,
                    "do_date_time": qatar_time,
                    "scheduled_date_time": qatar_time,
                    "do_number": trip.req_seq,
                    "do_ref_no": trip.req_seq,
                    "customer": {
                        "id": trip.customer_id.id,
                        "name": trip.customer_id.name,
                        "email": trip.task_id.sale_order_id.trip_sheet_email,  # take from so
                        "whatsapp_number": trip.task_id.sale_order_id.trip_sheet_whatsapp,  # take from so
                    },
                    "task": {
                        "id": trip.task_id.id,
                        "name": trip.task_id.name,
                        "contact": trip.task_id.contact_name,
                        "mobile": trip.task_id.contact_no,
                    },
                    "waste_type": {
                        "id": trip.waste_type_id.id,
                        "name": trip.waste_type_id.name,
                    },
                    "skip_type": {
                        "id": trip.equipment_type_id.id,
                        "name": trip.equipment_type_id.name,
                    },
                    "alternate_skips": alternate_skip_list,
                    "no_of_skips": trip.task_id.equipment_qty,
                    "frequency_id": trip.task_id.frequency_id.id,
                    "frequency": trip.task_id.frequency_id.name,
                    "vehicle": {
                        'id': trip.vehicle_no_id.id,
                        'name': trip.vehicle_no_id.name,
                    },
                    "driver": {
                        'id': trip.driver_id.id,
                        'name': trip.driver_id.name,
                    },
                    "helper_ids": helper_list,
                    # "weight": 0.0,
                    "land_fil": {
                        "id": trip.task_id.landfill_id.id,
                        "name": trip.task_id.landfill_id.name,
                    },
                    "state": trip.stage,
                    "type": trip.trip_type,
                    'location': location,
                    # "foc_paid_type": "foc"
                }
                data_list.append(vals)

        print('datalist+++++++++++++++++', data_list)
        return_result.update({
            'data': data_list
        })

        return return_result

    @http.route('/api/update-delivery-order', type='http', auth='public', methods=['POST'], csrf=False)
    def send_update_delivery_order_apis(self, **kwargs):
        token = request.httprequest.headers.get('Authorization')
        token_record = self.validate_token(token)
        if not token_record:
            return {
                "status": "Fail",
                "message": "Invalid Token.",
            }

        try:
            do_id = request.params.get('do_id')
            date_api = request.params.get('date')

            date_obj = fields.Datetime.from_string(date_api)

            date = date_obj - timedelta(hours=3)

            trip_type = request.params.get('trip_type')
            driver = request.params.get('driver')
            land_fill = request.params.get('land_fill')

            latitude = request.params.get('latitude')
            longitude = request.params.get('longitude')

            remark = request.params.get('remark')

            small_skip_delivered = request.params.get('small_skip_delivered')
            if small_skip_delivered:
                try:
                    if ',' in small_skip_delivered:
                        small_skip_delivered = [int(x.strip()) for x in small_skip_delivered.split(',') if x.strip()]
                    else:
                        small_skip_delivered = [int(small_skip_delivered.strip())]
                except Exception as e:
                    return Response(
                        json.dumps({'success': False, 'error': f'Invalid small_skip_delivered format: {str(e)}'}),
                        content_type="application/json", status=400)

            helper_ids = request.params.get('helper')
            if helper_ids:
                try:
                    if ',' in helper_ids:
                        helper_ids = [int(x.strip()) for x in helper_ids.split(',') if x.strip()]
                    else:
                        helper_ids = [int(helper_ids.strip())]
                except Exception as e:
                    return Response(
                        json.dumps({'success': False, 'error': f'Invalid helper_ids format: {str(e)}'}),
                        content_type="application/json", status=400)

            trip_sheet = request.env['custom.trip.sheet'].sudo().search([('id', '=', int(do_id))])

            if not trip_sheet:
                return Response(json.dumps({'status': 'error', 'message': 'Trip sheet not found'}),
                                content_type="application/json", status=404)

            skip_records = []
            image_files = request.httprequest.files.getlist('files')

            for image_file in image_files:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                skip_record = request.env['delivery.skip'].sudo().create({
                    'name': image_file.filename,
                    'file_content': image_base64,
                    'trip_id': trip_sheet.id,
                })
                skip_records.append(skip_record.id)

            small_skip_delivered_list = []
            for line in small_skip_delivered:
                vals = (0, 0, {
                    'billable': False,
                    'coll_del': 'delivery',
                    'maintenance_equ_id': line,
                    'qty': 1,
                    'equipment_qty': 1,
                })
                small_skip_delivered_list.append(vals)

            update_vals = {
                'date_from': date,
                'date_to': date,
                'trip_type': trip_type,
                'driver_id': int(driver),
                'latitude': latitude,
                'longitude': longitude,
                'landfill_id': int(land_fill),
                'remark': remark,
            }
            if helper_ids:
                update_vals['helper_ids'] = [(6, 0, helper_ids)]
            if skip_records:
                update_vals['delivery_skip_ids'] = [(6, 0, skip_records)]
            if small_skip_delivered_list:
                update_vals['skip_load_ids'] = small_skip_delivered_list

            trip_sheet.sudo().write(update_vals)
            trip_sheet.button_approve()

            return Response(
                json.dumps({'status': 'success', 'message': 'Trip sheet updated successfully', 'do_id': trip_sheet.id}),
                content_type="application/json", status=200)

        except Exception as e:
            return Response(json.dumps({'status': 'error', 'message': str(e)}), content_type="application/json",
                            status=500)

    @http.route('/api/collection-update-delivery-order', type='http', auth='public', methods=['POST'], csrf=False)
    def send_update_collection_delivery_order_apis(self, **kwargs):
        token = request.httprequest.headers.get('Authorization')
        token_record = self.validate_token(token)
        if not token_record:
            return {
                "status": "Fail",
                "message": "Invalid Token.",
            }

        try:
            do_id = request.params.get('do_id')
            date_api = request.params.get('date')

            date_obj = fields.Datetime.from_string(date_api)

            date = date_obj - timedelta(hours=3)

            trip_type = request.params.get('trip_type')
            driver = request.params.get('driver')
            land_fill = request.params.get('land_fill')

            latitude = request.params.get('latitude')
            longitude = request.params.get('longitude')
            no_manual_trips = request.params.get('no_manual_trips')
            final_collection = request.params.get('final_collection')
            final_collection = final_collection.lower() == 'true' if final_collection else False

            weight = request.params.get('weight')
            remark = request.params.get('remark')

            small_skip_delivered = request.params.get('small_skip_delivered')
            if small_skip_delivered:
                try:
                    if ',' in small_skip_delivered:
                        small_skip_delivered = [int(x.strip()) for x in small_skip_delivered.split(',') if x.strip()]
                    else:
                        small_skip_delivered = [int(small_skip_delivered.strip())]
                except Exception as e:
                    return Response(
                        json.dumps({'success': False, 'error': f'Invalid small_skip_delivered format: {str(e)}'}),
                        content_type="application/json", status=400)

            small_skip_collected = request.params.get('small_skip_collected')
            if small_skip_collected:
                try:
                    if ',' in small_skip_collected:
                        small_skip_collected = [int(x.strip()) for x in small_skip_collected.split(',') if x.strip()]
                    else:
                        small_skip_collected = [int(small_skip_collected.strip())]
                except Exception as e:
                    return Response(
                        json.dumps({'success': False, 'error': f'Invalid small_skip_collected format: {str(e)}'}),
                        content_type="application/json", status=400)

            helper_ids = request.params.get('helper')
            if helper_ids:
                try:
                    if ',' in helper_ids:
                        helper_ids = [int(x.strip()) for x in helper_ids.split(',') if x.strip()]
                    else:
                        helper_ids = [int(helper_ids.strip())]
                except Exception as e:
                    return Response(
                        json.dumps({'success': False, 'error': f'Invalid helper_ids format: {str(e)}'}),
                        content_type="application/json", status=400)

            trip_sheet = request.env['custom.trip.sheet'].sudo().search([('id', '=', int(do_id))])

            if not trip_sheet:
                return Response(json.dumps({'status': 'error', 'message': 'Trip sheet not found'}),
                                content_type="application/json", status=404)

            skip_records = []
            image_files = request.httprequest.files.getlist('files')

            for image_file in image_files:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                skip_record = request.env['delivery.skip'].sudo().create({
                    'name': image_file.filename,
                    'file_content': image_base64,
                    'trip_id': trip_sheet.id,
                })
                skip_records.append(skip_record.id)

            small_skip_list = []

            for line in small_skip_delivered:
                vals = (0, 0, {
                    'billable': False,
                    'coll_del': 'delivery',
                    'maintenance_equ_id': line,
                    'qty': 1,
                    'equipment_qty': 1,
                    # 'equipment_qty': int(no_manual_trips),
                })
                small_skip_list.append(vals)

            for line in small_skip_collected:
                vals = (0, 0, {
                    'billable': True,
                    'coll_del': 'collection',
                    'maintenance_equ_id': line,
                    'qty': 1,
                    'equipment_qty': 1,
                    # 'equipment_qty': int(no_manual_trips),
                })
                small_skip_list.append(vals)

            if not small_skip_collected and int(no_manual_trips) > 0:
                vals = (0, 0, {
                    'billable': True,
                    'coll_del': 'collection',
                    'maintenance_equ_id': False,
                    'qty': int(no_manual_trips),
                    'equipment_qty': int(no_manual_trips),
                })
                small_skip_list.append(vals)

            update_vals = {
                'date_from': date,
                'date_to': date,
                'final_collection': final_collection,
                'trip_type': trip_type,
                'latitude': latitude,
                'longitude': longitude,
                'driver_id': int(driver),
                'landfill_id': int(land_fill),
                'weight': float(weight),
                'remark': remark,
            }
            if helper_ids:
                update_vals['helper_ids'] = [(6, 0, helper_ids)]
            if skip_records:
                update_vals['delivery_skip_ids'] = [(6, 0, skip_records)]
            if small_skip_list:
                update_vals['skip_load_ids'] = small_skip_list

            trip_sheet.sudo().write(update_vals)
            trip_sheet.button_approve()

            return Response(
                json.dumps({'status': 'success', 'message': 'Trip sheet updated successfully', 'do_id': trip_sheet.id}),
                content_type="application/json", status=200)

        except Exception as e:
            return Response(json.dumps({'status': 'error', 'message': str(e)}), content_type="application/json",
                            status=500)

    @http.route('/api/create-visit-delivery-order', type='http', auth='public', methods=['POST'], csrf=False)
    def send_create_visit_delivery_order_apis(self, **kwargs):
        token = request.httprequest.headers.get('Authorization')
        token_record = self.validate_token(token)
        if not token_record:
            return {
                "status": "Fail",
                "message": "Invalid Token.",
            }

        try:
            vehicle_id = request.params.get('vehicle_id')
            shift_id = request.params.get('shift_id')
            task_id = request.params.get('task_id')
            date = request.params.get('date')
            weight = request.params.get('weight')
            land_fill = request.params.get('land_fill')
            trip_type = request.params.get('trip_type')
            driver = request.params.get('driver')
            remark = request.params.get('remark')

            # # Convert small_skip_delivered to list
            # small_skip_delivered = request.params.get('small_skip_delivered')
            # if small_skip_delivered:
            #     try:
            #         small_skip_delivered = ast.literal_eval(small_skip_delivered)
            #         if not isinstance(small_skip_delivered, list):
            #             small_skip_delivered = [int(small_skip_delivered)]
            #         else:
            #             small_skip_delivered = list(map(int, small_skip_delivered))
            #     except Exception as e:
            #         return Response(
            #             json.dumps({'success': False, 'error': f'Invalid small_skip_delivered format: {str(e)}'}),
            #             content_type="application/json", status=400)
            #
            # # Convert small_skip_collected to list
            # small_skip_collected = request.params.get('small_skip_collected')
            # if small_skip_collected:
            #     try:
            #         small_skip_collected = ast.literal_eval(small_skip_collected)
            #         if not isinstance(small_skip_collected, list):
            #             small_skip_collected = [int(small_skip_collected)]
            #         else:
            #             small_skip_collected = list(map(int, small_skip_collected))
            #     except Exception as e:
            #         return Response(
            #             json.dumps({'success': False, 'error': f'Invalid small_skip_collected format: {str(e)}'}),
            #             content_type="application/json", status=400)

            # Convert helper_ids to list
            helper_ids = request.params.get('helper')
            if helper_ids:
                try:
                    if ',' in helper_ids:
                        helper_ids = [int(x.strip()) for x in helper_ids.split(',') if x.strip()]
                    else:
                        helper_ids = [int(helper_ids.strip())]
                except Exception as e:
                    return Response(
                        json.dumps({'success': False, 'error': f'Invalid helper_ids format: {str(e)}'}),
                        content_type="application/json", status=400)

            # Create delivery.skip records for uploaded files
            skip_records = []
            image_files = request.httprequest.files.getlist('files')

            for image_file in image_files:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                skip_record = request.env['delivery.skip'].sudo().create({
                    'name': image_file.filename,
                    'file_content': image_base64,
                })
                skip_records.append(skip_record.id)

            # Prepare small skip delivery/collection records
            small_skip_list = []
            # for line in small_skip_delivered:
            #     vals = (0, 0, {
            #         'billable': False,
            #         'coll_del': 'delivery',
            #         'maintenance_equ_id': line,
            #         'qty': 1,
            #         'equipment_qty': 1,
            #     })
            #     small_skip_list.append(vals)
            #
            # for line in small_skip_collected:
            #     vals = (0, 0, {
            #         'billable': True,
            #         'coll_del': 'collection',
            #         'maintenance_equ_id': line,
            #         'qty': 1,
            #         'equipment_qty': 1,
            #     })
            #     small_skip_list.append(vals)

            small_skip_list = []
            vals = (0, 0, {
                'billable': False,
                'coll_del': 'visit',
                'maintenance_equ_id': False,
                'qty': 1,
                'equipment_qty': int(1),
            })
            small_skip_list.append(vals)

            # Create a new custom.trip.sheet record
            new_trip = request.env['custom.trip.sheet'].sudo().create({
                'schedule_date': date,
                'date_from': date,
                'date_to': date,
                'trip_type': trip_type,
                'driver_id': int(driver),
                'landfill_id': int(land_fill),
                'weight': float(weight),
                'vehicle_no_id': int(vehicle_id),
                'shift_id': int(shift_id),
                'task_id': int(task_id),
                'remark': remark,
                'helper_ids': [(6, 0, helper_ids)] if helper_ids else False,
                'delivery_skip_ids': [(6, 0, skip_records)] if skip_records else False,
                'skip_load_ids': small_skip_list if small_skip_list else False,
            })
            new_trip.sudo().update({
                'req_seq': new_trip.sequence,
            })
            new_trip.sudo().button_approve()

            return Response(json.dumps({
                'status': 'success',
                'message': 'Trip sheet created successfully',
                'trip_sheet_id': new_trip.id
            }), content_type="application/json", status=201)

        except Exception as e:
            return Response(json.dumps({'status': 'error', 'message': str(e)}), content_type="application/json",
                            status=500)

    def validate_token(self, token):
        token_new = token.replace("Bearer ", "")
        domain = [
            ('token', '=', token_new),
            ('expiration_date', '>', fields.Datetime.now()),
            # ('is_active', '=', True)
        ]

        token_record = request.env['employee.api.token'].sudo().search(domain, limit=1)
        if token_record:
            return token_record.employee_id
        return False
