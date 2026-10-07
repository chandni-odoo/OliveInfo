from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta

class FleetVehicleInherit(models.Model):
    _inherit = 'fleet.vehicle'
    
    capacity = fields.Integer(string="Seating Capacity")
    employee_allocation_ids = fields.One2many('fleet.employee.allocation', 'vehicle_id', string='Employee Allocations')
    employee_unallocation_ids = fields.One2many('fleet.employee.unallocation', 'vehicle_id', string='Employee UnAllocations')
    document_line_ids = fields.One2many('fleet.document.line', 'vehicle_id')
    task_id = fields.Many2one('project.task', string='Task')
    pickup_time = fields.Float(string='Pickup Time')
    drop_time = fields.Float(string='Drop Time')
    current_allocation_count = fields.Integer(compute='_compute_allocation_count', string='Current Allocations')
    remaining_capacity = fields.Integer(compute='_compute_allocation_count', string='Remaining Capacity')
    
    @api.depends('capacity', 'employee_allocation_ids')
    def _compute_allocation_count(self):
        for vehicle in self:
            active_allocations = self.env['fleet.employee.allocation'].search_count([
                ('vehicle_id', '=', vehicle.id),
                '|', ('end_date', '=', False), ('end_date', '>=', fields.Date.today())
            ])
            vehicle.current_allocation_count = active_allocations
            vehicle.remaining_capacity = max(0, vehicle.capacity - active_allocations)

    @api.onchange('task_id')
    def _onchange_task_id(self):
        if not self.task_id:
            self.employee_unallocation_ids = [(5, 0, 0)]
            return

        self.employee_unallocation_ids = [(5, 0, 0)]
        task_location = self.task_id.partner_location_id
        
        task_employees = self.env['hr.employee']
        for resource in self.task_id.resource_history_ids.filtered(lambda r: r.employee_id):
            task_employees |= resource.employee_id
        
        allocation_records = self.env['fleet.employee.allocation'].search([
            ('employee_id', 'in', task_employees.ids),
            '|', ('end_date', '=', False), ('end_date', '>=', fields.Date.today())
        ])
        
        employee_allocation_info = {}
        for alloc in allocation_records:
            employee_allocation_info[alloc.employee_id.id] = {
                'license_plate': alloc.license_plate,
                'vehicle_id': alloc.vehicle_id.id,
                'vehicle_name': alloc.vehicle_id.name,
                'start_date': alloc.start_date,
                'end_date': alloc.end_date
            }
        
        unallocation_lines = []
        for employee in task_employees:
            alloc_info = employee_allocation_info.get(employee.id, {})
            history = self.env['task.resource.history'].search([
                ('task_id', '=', self.task_id.id),
                ('employee_id', '=', employee.id)
                ], order='date_start desc', limit=1)
            unallocation_lines.append((0, 0, {
                'employee_id': employee.id,
                'task_id': self.task_id.id,
                'location_id': task_location.id if task_location else False,
                'selection': False,
                'start_date': fields.Date.to_date(history.date_start) if history and history.date_start else fields.Date.today(),
                'end_date': fields.Date.to_date(history.date_end) if history and history.date_end else False,
                # 'current_license_plate': alloc_info.get('license_plate', False),
                'current_vehicle_id': alloc_info.get('vehicle_id', False),
                'current_vehicle_name': alloc_info.get('vehicle_name', False),
            }))
        
        self.employee_unallocation_ids = unallocation_lines


    def write(self, vals):
        result = super(FleetVehicleInherit, self).write(vals)
        
        for vehicle in self:
            selected_unallocations = vehicle.employee_unallocation_ids.filtered(lambda x: x.selection)
            if not selected_unallocations:
                continue

            current_allocations = self.env['fleet.employee.allocation'].search_count([
                ('vehicle_id', '=', vehicle.id),
                '|', ('end_date', '=', False), ('end_date', '>=', fields.Date.today())
            ])
            
            if current_allocations + len(selected_unallocations) > vehicle.capacity:
                raise UserError(_(
                    "Cannot allocate %d employees. Vehicle capacity is %d. "
                    "Current allocations: %d. Remaining capacity: %d.") % (
                    len(selected_unallocations),
                    vehicle.capacity,
                    current_allocations,
                    max(0, vehicle.capacity - current_allocations)
                ))

            Allocation = self.env['fleet.employee.allocation']
            for unalloc in selected_unallocations:
                if Allocation.search_count([
                    ('employee_id', '=', unalloc.employee_id.id),
                    ('vehicle_id', '=', vehicle.id),
                    '|', ('end_date', '=', False), ('end_date', '>=', fields.Date.today())
                ]) > 0:
                    continue

                history = self.env['task.resource.history'].search([
                    ('task_id', '=', unalloc.task_id.id),
                    ('employee_id', '=', unalloc.employee_id.id)
                ], order='date_start desc', limit=1)

                Allocation.create({
                    'employee_id': unalloc.employee_id.id,
                    'location_id': unalloc.location_id.id,
                    'task_id': unalloc.task_id.id,
                    'vehicle_id': vehicle.id,
                    'pickup_time': vehicle.pickup_time,
                    'drop_time': vehicle.drop_time,
                    'license_plate': vehicle.license_plate,
                    'customer_id': unalloc.task_id.partner_id.id,
                    'sale_order_id': unalloc.task_id.sale_order_id.id if hasattr(unalloc.task_id, 'sale_order_id') else False,
                    'start_date': fields.Date.to_date(history.date_start) if history and history.date_start else fields.Date.today(),
                    'end_date': fields.Date.to_date(history.date_end) if history and history.date_end else False,
                    'demobilize_date': fields.Date.to_date(history.demobilize_date) if history and history.demobilize_date else False,
                })

            selected_unallocations.unlink()

            vehicle._compute_allocation_count()

        return result
    


    def _send_notifications(self, vehicle, expiring_docs, recipient_emails, tag_name):
        today = fields.Date.today()
        
        recipient_users = self.env['res.users'].search([
            ('login', 'in', recipient_emails)
        ])
        
        if not recipient_users:
            return
            
        activity_type = self.env['mail.activity.type'].sudo().search(
            [('name', '=', f'Vehicle Document Expiry - {tag_name}')], 
            limit=1
        )
        if not activity_type:
            activity_type = self.env['mail.activity.type'].sudo().create({
                'name': f'Vehicle Document Expiry - {tag_name}',
                'category': 'default'
            })
        
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', 'fleet.vehicle')], 
            limit=1
        )
        
        doc_list = "\n".join([
            f"- {doc.document_line_id.name} (Expires: {doc.valid_to})" 
            for doc in expiring_docs
        ])
        
        message = _(
            f"Vehicle %s (License: %s) has documents expiring soon:\n%s\n\n"
            "Please review and renew these documents."
        ) % (vehicle.name, vehicle.license_plate or 'N/A', doc_list)
        
        for user in recipient_users:
            self.env['bus.bus']._sendone(
                user.partner_id,
                'simple_notification',
                {
                    'title': f'{tag_name} Vehicle Document Expiry',
                    'message': f'{vehicle.name} has documents expiring soon',
                    'sticky': True,
                    'warning': True,
                }
            )
            
            existing_activity = self.env['mail.activity'].sudo().search([
                ('res_model_id', '=', model_id.id),
                ('res_id', '=', vehicle.id),
                ('user_id', '=', user.id),
                ('activity_type_id', '=', activity_type.id),
                ('state', '!=', 'done'),
            ], limit=1)
            
            if not existing_activity:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': model_id.id,
                    'res_model': 'fleet.vehicle',
                    'res_id': vehicle.id,
                    'user_id': user.id,
                    'activity_type_id': activity_type.id,
                    'summary': f'{tag_name} Vehicle Document Expiry',
                    'note': message,
                    'date_deadline': today,
                })

    def _check_document_expiry_notification(self):
        today = fields.Date.today()
        notification_date = today + relativedelta(days=30)
        
        tag_config = {
            'PS': {
                'recipients': [
                    'ahmed.alawi@dulsco.qa',
                    'dq.transportation@dulsco.qa',
                    'omer.elbashir@dulsco.qa',
                    'mohamed.shahat@dulsco.qa',
                    'manoj.kanchan@dulsco.qa'
                ]
            },
            'ES': {
                'recipients': [
                    'ajmal.ahmed@dulsco.qa',
                    'fayaz.ahmad@dulsco.qa',
                    'omer.elbashir@dulsco.qa',
                    'mohamed.shahat@dulsco.qa',
                    'manoj.kanchan@dulsco.qa'
                ]
            }
        }
        
        for tag_name, config in tag_config.items():
            vehicles = self.search([
                ('tag_ids.name', '=', tag_name),
                ('document_line_ids.valid_to', '<=', notification_date),
                ('document_line_ids.valid_to', '>=', today),
                ('document_line_ids.status', '=', 'active')
            ])
            
            for vehicle in vehicles:
                expiring_docs = vehicle.document_line_ids.filtered(
                    lambda d: d.valid_to <= notification_date and 
                              d.valid_to >= today and 
                              d.status == 'active'
                )
                
                if expiring_docs:
                    self._send_notifications(
                        vehicle, 
                        expiring_docs, 
                        config['recipients'], 
                        tag_name
                    )

    @api.model
    def _cron_check_document_expiry(self):
        self._check_document_expiry_notification()

    
    def _send_insurance_notifications(self, vehicle, expiring_insurances, recipient_emails, tag_name):
        today = fields.Date.today()
        
        recipient_users = self.env['res.users'].search([
            ('login', 'in', recipient_emails)
        ])
        
        if not recipient_users:
            return
            
        activity_type = self.env['mail.activity.type'].sudo().search(
            [('name', '=', f'Vehicle Insurance Expiry - {tag_name}')], 
            limit=1
        )
        if not activity_type:
            activity_type = self.env['mail.activity.type'].sudo().create({
                'name': f'Vehicle Insurance Expiry - {tag_name}',
                'category': 'default'
            })
        
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', 'fleet.vehicle')], 
            limit=1
        )
        
        insurance_list = "\n".join([
            f"- {insurance.insurance_company.name} (Policy: {insurance.policy_number}, Expires: {insurance.end_date})" 
            for insurance in expiring_insurances
        ])
        
        message = _(
            f"Vehicle %s (License: %s) has insurance policies expiring soon:\n%s\n\n"
            "Please review and renew these policies."
        ) % (vehicle.name, vehicle.license_plate or 'N/A', insurance_list)
        
        for user in recipient_users:
            self.env['bus.bus']._sendone(
                user.partner_id,
                'simple_notification',
                {
                    'title': f'{tag_name} Vehicle Insurance Expiry',
                    'message': f'{vehicle.name} has insurance expiring soon',
                    'sticky': True,
                    'warning': True,
                }
            )
            
            existing_activity = self.env['mail.activity'].sudo().search([
                ('res_model_id', '=', model_id.id),
                ('res_id', '=', vehicle.id),
                ('user_id', '=', user.id),
                ('activity_type_id', '=', activity_type.id),
                ('state', '!=', 'done'),
            ], limit=1)
            
            if not existing_activity:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': model_id.id,
                    'res_model': 'fleet.vehicle',
                    'res_id': vehicle.id,
                    'user_id': user.id,
                    'activity_type_id': activity_type.id,
                    'summary': f'{tag_name} Vehicle Insurance Expiry',
                    'note': message,
                    'date_deadline': today,
                })

    def _check_insurance_expiry_notification(self):
        today = fields.Date.today()
        notification_date = today + relativedelta(days=30)
        
        tag_config = {
            'PS': {
                'recipients': [
                    'ahmed.alawi@dulsco.qa',
                    'dq.transportation@dulsco.qa',
                    'omer.elbashir@dulsco.qa',
                    'mohamed.shahat@dulsco.qa',
                    'manoj.kanchan@dulsco.qa'
                ]
            },
            'ES': {
                'recipients': [
                    'ajmal.ahmed@dulsco.qa',
                    'fayaz.ahmad@dulsco.qa',
                    'omer.elbashir@dulsco.qa',
                    'mohamed.shahat@dulsco.qa',
                    'manoj.kanchan@dulsco.qa'
                ]
            }
        }
        
        for tag_name, config in tag_config.items():
            vehicles = self.search([
                ('tag_ids.name', '=', tag_name),
                ('vehicle_insurance_ids.end_date', '<=', notification_date),
                ('vehicle_insurance_ids.end_date', '>=', today),
            ])
            
            for vehicle in vehicles:
                expiring_insurances = vehicle.vehicle_insurance_ids.filtered(
                    lambda i: i.end_date <= notification_date and 
                             i.end_date >= today
                )
                
                if expiring_insurances:
                    self._send_insurance_notifications(
                        vehicle, 
                        expiring_insurances, 
                        config['recipients'], 
                        tag_name
                    )

    @api.model
    def _cron_check_insurance_expiry(self):
        self._check_insurance_expiry_notification()


class EmployeeAllocation(models.Model):
    _name = 'fleet.employee.allocation'
    _description = 'Fleet Employee Allocation'
    _order = 'end_date asc'  
    
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer')
    location_id = fields.Many2one('contact.location', string='Location')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    task_id = fields.Many2one('project.task', string='Task')
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date')
    demobilize_date = fields.Date(string='Demobilize Date')
    pickup_time = fields.Float(string='Pickup Time')
    drop_time = fields.Float(string='Drop Time')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    can_select = fields.Boolean(string="Can Select", compute='_compute_can_select', store=True)
    license_plate = fields.Char(related='vehicle_id.license_plate', string='License Plate', store=True, readonly=True)
    active = fields.Boolean(string="Active", default=True, compute='_compute_active', store=True)

    @api.depends('end_date')
    def _compute_active(self):
        today = fields.Date.today()
        for record in self:
            record.active = not record.end_date or record.end_date >= today

    @api.depends('vehicle_id.remaining_capacity')
    def _compute_can_select(self):
        for record in self:
            record.can_select = record.vehicle_id.remaining_capacity > 0


class EmployeeUnAllocation(models.Model):
    _name = 'fleet.employee.unallocation'
    _description = 'Fleet Employee UnAllocation'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    location_id = fields.Many2one('contact.location', string='Location')
    task_id = fields.Many2one('project.task', string='Task')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    selection = fields.Boolean(string="Select")
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date')
    license_plate = fields.Char(related='vehicle_id.license_plate', string='License Plate', store=True, readonly=True)
    # current_license_plate = fields.Char(string='Currently Allocated Vehicle', readonly=True)
    current_vehicle_id = fields.Many2one('fleet.vehicle', string='Current Vehicle', readonly=True)
    current_vehicle_name = fields.Char(related='current_vehicle_id.name', string='Current Vehicle Name', readonly=True)


class HrDocumentLine(models.Model):
    _name = 'fleet.document.line'
    _description = "fleet Document Line"


    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    license_plate = fields.Char(related='vehicle_id.license_plate', string='License Plate', store=True, readonly=True)
    document_line_id = fields.Many2one('hr.document', 'Document Type')
    document_number = fields.Char('Document No')
    valid_from = fields.Date()
    valid_to = fields.Date()
    doc_issue_place = fields.Char('Document Place ')
    status = fields.Selection([('active', 'Active'), ('history', 'History')], default='active')
    remarks = fields.Char()
    attachment = fields.Binary('Attachment')


