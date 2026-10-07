# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError


class MailCompose(models.TransientModel):
    _inherit = "mail.compose.message"

    corrective_action = fields.Boolean(string="Corrective Action")
    preventive_action = fields.Boolean(string="Preventive Action")
    resolution_action = fields.Boolean(string="Resolution")

    @api.onchange('corrective_action', 'preventive_action', 'resolution_action')
    def _onchange_corrective(self):
        if self.env.context.get('default_model') == 'helpdesk.ticket':
            template_name = False

            if self.corrective_action:
                if self.preventive_action and self.resolution_action:
                    template_name = 'Closing Ticket'
                elif not self.preventive_action and self.resolution_action:
                    template_name = 'Corrective and Resolution'
                elif self.preventive_action and not self.resolution_action:
                    template_name = 'Corrective and Preventive'
                else:
                    template_name = 'Closing Ticket Corrective'
            else:
                if self.preventive_action and self.resolution_action:
                    template_name = 'Preventive and Resolution'
                elif not self.preventive_action and self.resolution_action:
                    template_name = 'Closing Ticket Resolution'
                elif self.preventive_action and not self.resolution_action:
                    template_name = 'Closing Ticket Preventive'
                else:
                    template_name = 'Opening Template'

            if template_name:
                mail_template = self.env['mail.template'].search([('name', '=', template_name)], limit=1)
                self.template_id = mail_template.id if mail_template else False

        # if self.preventive_action == True:
        #     if self.corrective_action == True and self.resolution_action == True:
        #         mail_template = self.env['mail.template'].search([('name', '=', 'Closing Ticket')],limit=1)
        #         print ("condition 99999999999",mail_template)
        #     elif self.corrective_action == False and self.resolution_action == True:
        #         mail_template = self.env['mail.template'].search([('name', '=', 'Corrective and Resolution')],limit=1)
        #         print ("condition 1000000",mail_template)
        #     elif self.corrective_action == True and self.resolution_action == False:
        #         mail_template = self.env['mail.template'].search([('name', '=', 'Corrective and Preventive')],limit=1)
        #         print ("mail_template 11 11  11  11",mail_template)
        #     else:
        #         mail_template = self.env['mail.template'].search([('name', '=', 'Closing Ticket Corrective')],limit=1)
        #         print ("mail_template_+12 12 12 12 12 12",mail_template)
        # elif self.preventive_action == False:
        #     if self.corrective_action == True and self.resolution_action == True:
        #         mail_template = self.env['mail.template'].search([('name', '=', 'Preventive and Resolution')],limit=1)
        #         print ("mail_template+ 13 13 13 13 13 13 13 ",mail_template)
        #     elif self.corrective_action == False and self.resolution_action == True:
        #         mail_template = self.env['mail.template'].search([('name', '=', 'Closing Ticket Resolution')],limit=1)
        #         print ("mail_template 14 14 14 14 14 14 ",mail_template)
        #     elif self.corrective_action == True and self.resolution_action == False:
        #         mail_template = self.env['mail.template'].search([('name', '=', 'Closing Ticket Preventive')],limit=1)
        #         print ("mail_template15 15 15 15 15 15 ",mail_template)
        #     else:
        #         mail_template = self.env['mail.template'].search([('name', '=', 'Opening Customer Ticket')],limit=1)
        #         print ("mail_template 16 16 16 16 16 16 16",mail_template)
        # self.template_id = mail_template.id
                
                
        #         
        #         print('mail templateh7tutjb6bkn7k7k7k7 k7k__________', mail_template)
        #         mail_template = self.env['mail.template'].search([('name', '=', 'Closing Ticket Corrective')],limit=1)
        #         print('mail templateh7tutjb6bkn7k7k7k7 k7k__________', mail_template)
        #     self.template_id = mail_template.id
        # if self.corrective_action and self.preventive_action and self.resolution_action:
        #     mail_template = self.env['mail.template'].search([('name', 'like', 'Closing Ticket Resolution')],
        #                                                      limit=1)
        #     print('mail templateh7tutjb6bkn7k7k7k7 k7k__________', mail_template)
        #     self.template_id = mail_template.id
        # else:
        #     if self.corrective_action:
        #         if self.corrective_action and self.preventive_action:
        #             print('corrective and preventive  111111_____________________')
        #             mail_template = self.env['mail.template'].search([('name', 'like', 'Corrective and Preventive')],
        #                                                              limit=1)
        #             print('mail template__________', mail_template)
        #             self.template_id = mail_template.id
        #         elif self.corrective_action and self.resolution_action:
        #             print('corrective and resolution 222222________________')
        #             mail_template = self.env['mail.template'].search([('name', 'like', 'Corrective and Resolution')],
        #                                                              limit=1)
        #             print('mail template__________', mail_template)
        # 
        #             self.template_id = mail_template.id
        #         else:
        #             print('corrective______________33333333')
        #             mail_template = self.env['mail.template'].search([('name', 'like', 'Closing Ticket Corrective')],
        #                                                              limit=1)
        #             print('mail template11__________', mail_template)
        # 
        #             # active_ids = self.env.context.get('active_ids')
        #             # print('active ids__________________', active_ids)
        #             # helpdesk = self.env['helpdesk.ticket'].browse(active_ids)
        #             self.template_id = mail_template.id
        #     elif self.preventive_action:
        #         if self.preventive_action and self.resolution_action:
        #             print('corrective and preventive 444444_____________________')
        #             mail_template = self.env['mail.template'].search([('name', 'like', 'Preventive and Resolution')],
        #                                                              limit=1)
        #             print('mail template__________', mail_template)
        # 
        #             self.template_id = mail_template.id
        # 
        #         elif self.preventive_action and self.corrective_action:
        #             print('corrective and resolution 555555________________')
        #             mail_template = self.env['mail.template'].search([('name', 'like', 'Corrective and Preventive')],
        #                                                              limit=1)
        #             print('mail template__________', mail_template)
        # 
        #             self.template_id = mail_template.id
        # 
        #         else:
        #             print('preventive 66666666______________')
        #             mail_template = self.env['mail.template'].search([('name', 'like', 'Closing Ticket Preventive')],
        #                                                              limit=1)
        #             print('mail template2 ________________', mail_template)
        #             self.template_id = mail_template.id
        #     elif self.resolution_action:
        #         if self.resolution_action and self.preventive_action:
        #             print('corrective and preventive  777777777_____________________')
        #             mail_template = self.env['mail.template'].search([('name', 'like', 'Preventive and Resolution')],
        #                                                              limit=1)
        #             print('mail template__________', mail_template)
        # 
        #             self.template_id = mail_template.id
        # 
        #         elif self.resolution_action and self.corrective_action:
        #             print('corrective and resolution 888888________________')
        #             mail_template = self.env['mail.template'].search([('name', 'like', 'Corrective and Resolution')],
        #                                                              limit=1)
        #             print('mail template__________', mail_template)
        # 
        #             self.template_id = mail_template.id
        #         else:
        #             print('resolution 99999999______________')
        #             mail_template = self.env['mail.template'].search([('name', 'like', 'Closing Ticket Resolution')],
        #                                                              limit=1)
        #             print('mail template3 ________________', mail_template)
        #             self.template_id = mail_template.id

    # @api.onchange('preventive_action')
    # def _onchange_preventive(self):
    #     if self.preventive_action:
    #         if self.preventive_action and self.resolution_action:
    #             print('corrective and preventive 444444_____________________')
    #             mail_template = self.env['mail.template'].search([('name', 'like', 'Preventive and Resolution')],
    #                                                              limit=1)
    #             print('mail template__________', mail_template)
    #
    #             self.template_id = mail_template.id
    #
    #         elif self.preventive_action and self.corrective_action:
    #             print('corrective and resolution 555555________________')
    #             mail_template = self.env['mail.template'].search([('name', 'like', 'Corrective and Preventive')],
    #                                                              limit=1)
    #             print('mail template__________', mail_template)
    #
    #             self.template_id = mail_template.id
    #
    #         else:
    #             print('preventive 66666666______________')
    #             mail_template = self.env['mail.template'].search([('name', 'like', 'Closing Ticket Preventive')],
    #                                                              limit=1)
    #             print('mail template2 ________________', mail_template)
    #             self.template_id = mail_template.id
    #
    # @api.onchange('resolution_action')
    # def _onchange_resolution(self):
    #     if self.resolution_action:
    #         if self.resolution_action and self.preventive_action:
    #             print('corrective and preventive  777777777_____________________')
    #             mail_template = self.env['mail.template'].search([('name', 'like', 'Preventive and Resolution')],
    #                                                              limit=1)
    #             print('mail template__________', mail_template)
    #
    #             self.template_id = mail_template.id
    #
    #         elif self.resolution_action and self.corrective_action:
    #             print('corrective and resolution 888888________________')
    #             mail_template = self.env['mail.template'].search([('name', 'like', 'Corrective and Resolution')],
    #                                                              limit=1)
    #             print('mail template__________', mail_template)
    #
    #             self.template_id = mail_template.id
    #
    #         else:
    #             print('resolution 99999999______________')
    #             mail_template = self.env['mail.template'].search([('name', 'like', 'Closing Ticket Resolution')],
    #                                                              limit=1)
    #             print('mail template3 ________________', mail_template)
    #             self.template_id = mail_template.id
