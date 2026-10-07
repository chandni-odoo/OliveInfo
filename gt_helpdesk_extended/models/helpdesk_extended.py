# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
import re
from datetime import date

class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"
    _description = 'Helpdesk'

    branch_id = fields.Many2one('res.branch', string="Branch")
    corrective_action = fields.Html(string="Corrective Action")
    preventive_action = fields.Html(string="Preventive Action")
    resolution_action = fields.Html(string="Resolution Action")
    employee_complaints = fields.Boolean(string='Employee Outsourcing Complaints')
    hse_complaints = fields.Boolean(string='HSE Complaints')
    it_support = fields.Boolean(string='IT Support')
    waste_management = fields.Boolean(string='Waste Management')
    done_stage_boolean = fields.Boolean(compute='_compute_stage_data_done', store=True)
    new_stage = fields.Boolean(string='New Stage', default=True)
    is_validate = fields.Boolean(string='Is Validate')
    ticket_date = fields.Date(string="Ticket Date", default=date.today())

    @api.onchange('sub_desk_type')
    def onchange_sub_desk_type(self):
        self.description = self.sub_desk_type.description

    # sla_escalation_date = fields.Date(string='SLA Escalation Date')

    # overwriting default function to remove user_id on default
    @api.model
    def default_get(self, fields):
        result = super(HelpdeskTicket, self).default_get(fields)
        if result.get('team_id') and fields:
            team = self.env['helpdesk.team'].browse(result['team_id'])
            if 'user_id' in fields and 'user_id' not in result:  # if no user given, deduce it from the team
                result['user_id'] = team._determine_user_to_assign()[team.id].id
            if 'stage_id' in fields and 'stage_id' not in result:  # if no stage given, deduce it from the team
                result['stage_id'] = team._determine_stage()[team.id].id
            result['user_id'] = []
        return result

    # overwriting default function to remove user_id on default
    @api.depends('team_id')
    def _compute_user_and_stage_ids(self):
        print("calling default overwritted function")
        for ticket in self.filtered(lambda ticket: ticket.team_id):
            print("ticket+_+_+_+_user", ticket.user_id)
            if not ticket.stage_id or ticket.stage_id not in ticket.team_id.stage_ids:
                ticket.stage_id = ticket.team_id._determine_stage()[ticket.team_id.id]

    @api.depends('stage_id')
    def _compute_stage_data_done(self):
        for rec in self:
            if rec.stage_id.name == 'Done':
                if rec.done_stage_boolean == False:
                    rec.done_stage_boolean = True

    def assign_or_reassign(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'assign.or.reassing',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
        }

    def send_mail_to_customers(self):
        """ Opens a wizard to compose an email, with relevant mail template loaded by default """
        self.ensure_one()
        # self.order_line._validate_analytic_distribution()
        lang = self.env.context.get('lang')
        mail_template = self.env['mail.template'].search([('name', 'like', 'Opening Template')], limit=1)
        print('mail template open close_______________', mail_template)
        ctx = {
            'default_model': 'helpdesk.ticket',
            'default_res_ids': self.ids,
            'default_partner_ids': self.partner_id.ids,
            'default_template_id': mail_template.id if mail_template else mail_template,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    @api.onchange('ticket_type_id')
    def onchange_ticket_type(self):
        if self.ticket_type_id.name == 'Employee Outsourcing Complaints':
            self.employee_complaints = True
            self.hse_complaints = False
            self.it_support = False
            self.waste_management = False

        elif self.ticket_type_id.name == 'HSE Complaints':
            self.hse_complaints = True
            self.employee_complaints = False
            self.it_support = False
            self.waste_management = False

        elif self.ticket_type_id.name == 'IT Support':
            self.it_support = True
            self.employee_complaints = False
            self.hse_complaints = False
            self.waste_management = False

        elif self.ticket_type_id.name == 'Waste Management':
            self.waste_management = True
            self.employee_complaints = False
            self.hse_complaints = False
            self.it_support = False
        else:
            False

    def check_description(self):
        print('self++++++++++++++++++', self)
        print('self++++++++++++++++++', self.description)
        if self.description:
            text = re.compile('<.*?>')
            message = re.sub(text, '', self.description)
            print('message++++++++++++++', message)
            if message:
                return True
            else:
                return False
        else:
            return False

    @api.model
    def create(self, vals):
        if 'ticket_type_id' in vals:
            type_id = self.env['helpdesk.ticket.type'].browse(vals['ticket_type_id'])
        res = super(HelpdeskTicket, self).create(vals)
        #res.write({'description': res.sub_desk_type.description})
        print("BEFORE MANAGER NOTIFICATION")
        if res.ticket_type_id and res.ticket_type_id.manager_id:
            print("Creating Manager Notification")
            self.create_manager_notification(res, res.ticket_type_id.manager_id)
        return res

    def write(self, vals):
        print("vals__+_+_+_+_+_+_+write function", vals)
        if 'user_id' in vals:
            if vals['user_id'] != False:
                stage = self.env['helpdesk.stage'].search([('name', '=', 'In Progress')], limit=1)
                print('stage________________', stage, stage.name, self.stage_id.name)
                if stage and self.stage_id.name == 'New':
                    print("stage.name_)_)_)_)GOING IN IFFFF")
                    vals.update({
                        'stage_id': stage.id,
                        'new_stage': False,
                    })

                else:
                    vals.update({
                        'new_stage': False,
                    })
                print("vals+_+_+_+_+", vals)
                print("self.user_id+__+_", self.user_id)
                if self.user_id:
                    activity_type_id = self.env['mail.activity.type'].sudo().search(
                        [('name', '=', 'Helpdesk Ticket Assigned')], limit=1)
                    model_id = self.env['ir.model'].sudo().search([('model', '=', 'helpdesk.ticket')], limit=1)
                    activity_id = self.env['mail.activity'].sudo().search(
                        [('res_model_id', '=', model_id.id), ('res_model', '=', 'helpdesk.ticket'),
                         ('res_id', '=', self.id), ('user_id', '=', self.user_id.id)])
                    print("activity_id+_+_+_IN IFIFIFIF", activity_id)
                    if activity_id:
                        activity_id.unlink()
                self.mail_notification_assignee(self, vals['user_id'])
                # mail_temp = self.env.ref('gt_helpdesk_extended.send_mail_to_assignee')
                # mail_temp.send_mail(self.id, force_send=True)
                # new line
                # self.with_context(force_send=True).message_post_with_template(mail_temp.id, composition_mode='comment')
            else:
                print("going ingingignin ELSE LESE ELSE")
                stage = self.env['helpdesk.stage'].search([('name', '=', 'New')], limit=1)
                print('stage________________', stage, stage.name)
                if stage and self.stage_id.name != 'New':
                    print("going IFIFIFIFI ELSE ELSE ELSE")
                    vals.update({
                        'stage_id': stage.id,
                        'new_stage': True,
                    })

                    if self.user_id:
                        activity_type_id = self.env['mail.activity.type'].sudo().search(
                            [('name', '=', 'Helpdesk Ticket Assigned')], limit=1)
                        model_id = self.env['ir.model'].sudo().search([('model', '=', 'helpdesk.ticket')], limit=1)
                        activity_id = self.env['mail.activity'].sudo().search(
                            [('res_model_id', '=', model_id.id), ('res_model', '=', 'helpdesk.ticket'),
                             ('res_id', '=', self.id), ('user_id', '=', self.user_id.id)])
                        if activity_id:
                            activity_id.unlink()
        res = super(HelpdeskTicket, self).write(vals)
        return res

    def create_manager_notification(self, res, user):
       # model_id = self.env['ir.model'].search([('model', '=', 'helpdesk.ticket')], limit=1)
        activity_type_id = self.env['mail.activity.type'].search([('name', '=', 'Helpdesk Ticket To Be Assign')],
                                                                        limit=1)
        print("self.user_id.id_+_+_+_+_+_", res, user)
        activity_vals = {'res_model_id': self.env['ir.model']._get('helpdesk.ticket').id,
                         'res_id': res.id,
                         'res_name': 'Helpdesk Ticket To Be Assigned',
                         'user_id': user.id,
                         'activity_type_id': activity_type_id.id,
                         'date_deadline': fields.Date.today(self),
                         }
        print("activity_vals+_+_+_+", activity_vals)
        activity_id = self.env['mail.activity'].create(activity_vals)
        print("activity_id+_+_+_+_+_", activity_id)

    def mail_notification_assignee(self, res, user):
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'helpdesk.ticket')], limit=1)
        activity_type_id = self.env['mail.activity.type'].sudo().search([('name', '=', 'Helpdesk Ticket Assigned')],
                                                                        limit=1)
        print("self.user_id.id_+_+_+_+_+_", res.user_id, self)
        activity_vals = {'res_model_id': model_id.id,
                         'res_model': 'helpdesk.ticket',
                         'res_id': res.id,
                         'res_name': 'Helpdesk Ticket Assigned',
                         'user_id': user,
                         'activity_type_id': activity_type_id.id,
                         'date_deadline': (fields.Datetime.today()).strftime('%Y-%m-%d %H:%M')
                         }
        print("activity_vals+_+_+_+_+", activity_vals)
        activity_id = self.env['mail.activity'].sudo().search(
            [('res_model_id', '=', model_id.id), ('res_model', '=', 'helpdesk.ticket'),
             ('res_id', '=', res.id), ('user_id', '=', user)])
        print("activity_id+_+_+_+_+creating++notification", activity_id)
        if not activity_id:
            activity_id = self.env['mail.activity'].create(activity_vals)
            print("activity_id+_+_+_+_+_creating", activity_id)

    # @api.model
    # def create(self, vals):
    #     res = super(HelpdeskTicket, self).create(vals)
    #     if res.ticket_type_id:
    #         domain = [('ticket_type_id', '=', res.ticket_type_id.id)]
    #     if res.sub_desk_type:
    #         domain.append(('sub_type_id', '=', res.sub_desk_type.id))
    #     if res.partner_id:
    #         domain.append(('partner_ids', '=', res.partner_id.id))
    #
    #     print('domain+++++++++++++++++++', domain)
    #
    #     sla_status_ids = []
    #
    #     helpdesk_sla = self.env['helpdesk.sla'].search(domain)
    #     print('helpdesk_sla+++++++++++++', helpdesk_sla)
    #
    #     for sla in helpdesk_sla:
    #         helpdesk_sla_status = self.env['helpdesk.sla.status'].search([('sla_id', '=', sla.id)])
    #         print('helpdesk_sla_status+++++++++++++', helpdesk_sla_status)
    #         sla_status_ids.append(helpdesk_sla_status.id)
    #
    #     print('sla_status_ids+++++++++++++', sla_status_ids)
    #     # res.write({"sla_status_ids": [(6, 0, sla_status_ids)]})
    #     res.write({"sla_status_ids": [(4, 106)]})

    def _sla_find(self):
        """ Find the SLA to apply on the current tickets
            :returns a map with the tickets linked to the SLA to apply on them
            :rtype : dict {<helpdesk.ticket>: <helpdesk.sla>}
        """
        tickets_map = {}
        sla_domain_map = {}

        def _generate_key(ticket):
            """ Return a tuple identifying the combinaison of field determining the SLA to apply on the ticket """
            fields_list = self._sla_reset_trigger()
            key = list()
            for field_name in fields_list:
                if ticket._fields[field_name].type == 'many2one':
                    key.append(ticket[field_name].id)
                else:
                    key.append(ticket[field_name])
            return tuple(key)

        for ticket in self:
            if ticket.team_id.use_sla:  # limit to the team using SLA
                key = _generate_key(ticket)
                # group the ticket per key
                tickets_map.setdefault(key, self.env['helpdesk.ticket'])
                tickets_map[key] |= ticket
                # group the SLA to apply, by key
                if key not in sla_domain_map:
                    sla_domain_map[key] = expression.AND([[
                        ('team_id', '=', ticket.team_id.id), ('priority', '<=', ticket.priority),
                        ('stage_id.sequence', '>=', ticket.stage_id.sequence),
                        '|', ('ticket_type_id', '=', ticket.ticket_type_id.id), ('ticket_type_id', '=', False),
                        '|', ('sub_type_id', '=', ticket.sub_desk_type.id), ('sub_type_id', '=', False)],
                        ticket._sla_find_extra_domain()])

        result = {}
        for key, tickets in tickets_map.items():  # only one search per ticket group
            domain = sla_domain_map[key]

            print('domain__________________', domain)

            slas = self.env['helpdesk.sla'].search(domain)
            result[tickets] = slas.filtered(lambda s: s.tag_ids <= tickets.tag_ids)  # SLA to apply on ticket subset
        return result


class HelpdeskTicketType(models.Model):
    _inherit = 'helpdesk.ticket.type'

    manager_id = fields.Many2one('res.users', string='Manager')


class HelpdeskTicketSubType(models.Model):
    _inherit = 'helpdesk.ticket.sub.type'

    description = fields.Html(string='Description')


