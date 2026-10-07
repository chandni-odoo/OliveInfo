# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html2plaintext

class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    
    project_id = fields.Many2one('project.project', related='task_name.project_id', string='Project')
    task_name = fields.Many2one('project.task',domain="""['&',('project_id.partner_id', '=', partner_id),('job_stage_category', 'in', ['warning', 'muted'])]""", string="Task",context="{'show_extra_fields': True}")
    emp_id = fields.Many2one('hr.employee', string='Employee')
    equipment_id = fields.Many2one("maintenance.equipment", "Equipment", help="Select Equipment")
    sub_desk_type = fields.Many2one('helpdesk.ticket.sub.type',domain="[('ticket_type_id', '=', ticket_type_id)]",string="Sub Type")

    custom_trip_id = fields.Many2one('custom.trip.sheet', string='Related Trip Sheet', readonly=True)
    req_seq = fields.Char(string='Request Sequence', readonly=True) 
    

    @api.model
    def create(self, vals):
        ticket = super(HelpdeskTicket, self).create(vals)
        
        if (ticket.ticket_type_id and ticket.ticket_type_id.name and 
            ticket.ticket_type_id.name.lower() == 'waste management' and 
            ticket.sub_desk_type and ticket.sub_desk_type.sub_type_name and 
            ticket.sub_desk_type.sub_type_name.lower() == 'bin requests' and 
            not ticket.custom_trip_id):
            
            trip_vals = ticket._prepare_custom_trip_vals()
            custom_trip = self.env['custom.trip.sheet'].create(trip_vals)
            ticket.custom_trip_id = custom_trip.id

            if custom_trip and hasattr(custom_trip, 'sequence'):
                ticket.req_seq = custom_trip.sequence

            ticket.write({
                'custom_trip_id': custom_trip.id,
                'req_seq': custom_trip.sequence  
            })
            
        return ticket
    
    
    def _prepare_custom_trip_vals(self):

        plain_description = html2plaintext(self.description) if self.description else ""

        contact_info = []
        if self.partner_phone:
            contact_info.append(f"Phone: {self.partner_phone}")
        if self.partner_email:
            contact_info.append(f"Email: {self.partner_email}")
        
        contact_str = "\n".join(contact_info) if contact_info else "No contact information"
        return {
            'stage': 'draft',  
            'trip_type': 'trip',
            'schedule_date': self.ticket_date,
            'customer_id': self.partner_id.id,
            'task_id': self.task_name.id if self.task_name else False,
            'partner_id': self.partner_id.id,
            'call_date': self.ticket_date,
            'requested_by': self.partner_name or self.partner_id.name,
            'on_call': True,
            'on_call_pending': True,
            'mobile': contact_str,
            'remark': plain_description,
        }
        
    

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id :
            self.project_id = False
            self.task_name = False

class HelpdeskSubType(models.Model):
    _name = 'helpdesk.ticket.sub.type'
    _rec_name = 'sub_type_name'
    
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string='Parent Type')
    sub_type_name = fields.Char('Sub Type')

class ProjectTask(models.Model):
    _inherit = 'project.task'
    
    # def name_get(self):
    #     result = []
    #     for task in self:
    #         name = task.name
    #         if self._context.get('show_extra_fields'):
    #             extra_info = []
    #             if task.seq_code:
    #                 extra_info.append(f"[{task.seq_code}]")
    #             if task.partner_location_id:
    #                 extra_info.append(f"Loc: {task.partner_location_id.display_name}")
    #             if task.vehicle_type_id:
    #                 extra_info.append(f"Veh: {task.vehicle_type_id.display_name}")
    #             if task.waste_type_id:
    #                 extra_info.append(f"Waste: {task.waste_type_id.display_name}")
    #             if task.equipment_type_id:
    #                 extra_info.append(f"Eq: {task.equipment_type_id.display_name}")
                
    #             if extra_info:
    #                 name = f"{name} {' '.join(extra_info)}"
    #         result.append((task.id, name))
    #     return result


class CustomTripSheet(models.Model):
    _inherit = "custom.trip.sheet"
    _rec_name = 'sequence'


    on_call_pending = fields.Boolean(string="On Call Pending", default=False)

    @api.model
    def create(self, vals):
        if vals.get('sequence', _('New')) == _('New'):
            vals['sequence'] = self.env['ir.sequence'].next_by_code('custom.trip.sheet') or _('New')
        
        if 'req_seq' not in vals:
            vals['req_seq'] = vals.get('sequence')
            
        return super(CustomTripSheet, self).create(vals)

