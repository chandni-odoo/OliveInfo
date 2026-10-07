from odoo import models, fields, api
from odoo.tools import date_utils
import io
import json
from datetime import date

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class EmployeeAllocationReport(models.TransientModel):
    _name = 'employee.allocation.report'
    _description = 'Employee Allocation Report'

    report_date = fields.Date(string='Report Date', required=True, default=fields.Date.today)
    vehicle_ids = fields.Many2many('fleet.vehicle', string='Vehicles')
    # employee_ids = fields.Many2many('hr.employee', string='Employees')
    customer_ids = fields.Many2many('res.partner', string='Customers')
    sale_order_ids = fields.Many2many('sale.order', string='Sale Orders')

    def action_print_report(self):
        return self._print_report()

    def _print_report(self):
        data = {
            'report_date': self.report_date,
            'vehicle_ids': self.vehicle_ids.ids,
            # 'employee_ids': self.employee_ids.ids,
            'customer_ids': self.customer_ids.ids,
            'sale_order_ids': self.sale_order_ids.ids,
        }
        return self.env.ref('fleet_extended.employee_allocation_report_xlsx').report_action(self, data=data)

    def get_report_data(self, data):
        domain = [
            ('start_date', '<=', data['report_date']),
            '|',
            ('end_date', '=', False),
            ('end_date', '>=', data['report_date']),
        ]
        
        if data.get('vehicle_ids'):
            domain.append(('vehicle_id', 'in', data['vehicle_ids']))
        # if data.get('employee_ids'):
        #     domain.append(('employee_id', 'in', data['employee_ids']))
        if data.get('customer_ids'):
            domain.append(('customer_id', 'in', data['customer_ids']))
        if data.get('sale_order_ids'):
            domain.append(('sale_order_id', 'in', data['sale_order_ids']))
            
        allocations = self.env['fleet.employee.allocation'].search(domain, order='vehicle_id, start_date')
        
        report_data = []
        for alloc in allocations:
            report_data.append({
                'vehicle': alloc.vehicle_id.name,
                'license_plate': alloc.license_plate,
                'employee': alloc.employee_id.name,
                'customer': alloc.customer_id.name if alloc.customer_id else '',
                'sale_order': alloc.sale_order_id.name if alloc.sale_order_id else '',
                'task': alloc.task_id.name if alloc.task_id else '',
                'location': alloc.location_id.name if alloc.location_id else '',
                'start_date': alloc.start_date,
                'end_date': alloc.end_date or 'Ongoing',
                'demobilize_date': alloc.demobilize_date if alloc.demobilize_date else '', 
                'pickup_time': alloc.pickup_time,
                'drop_time': alloc.drop_time,
            })
            
        return report_data