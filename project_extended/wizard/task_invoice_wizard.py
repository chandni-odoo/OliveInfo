from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import ValidationError, UserError

class TaskInvoiceWizard(models.TransientModel):
    _name = "task.invoice.wizard"
    _description="Task invoice"

    journal_id = fields.Many2one('account.journal', string="Journal", required=True)
    partner_id = fields.Many2many('res.partner', string="Customer", required=True)

    @api.model
    def default_get(self, fields_list):
        res = super(TaskInvoiceWizard, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            task_ids = self.env['project.task'].browse(active_ids)
            journal_domain = [
                ('type', '=', 'sale'),
                ('company_id', '=', self.env.user.company_id.id),
            ]
            customer_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            if not customer_journal_id:
                raise ValidationError(_('Sale type journal is not found'))
            partner_id = task_ids.mapped('partner_id')
            res['journal_id'] = customer_journal_id
            res['partner_id'] = partner_id
        return res

    def create_task_invoice(self):
        invoice = self.env['account.move']
        active_ids = self.env.context.get('active_ids')
        task_ids = self.env['project.task'].browse(active_ids)
        product_special_ot = self.env.ref('project_extended.product_soc_product_template')
        product_normal_ot = self.env.ref('project_extended.product_noc_product_template')
        # product_special_ot = self.env['product.product'].search([('default_code', '=', 'SOC')], limit=1)
        # product_normal_ot = self.env['product.product'].search([('default_code', '=', 'NOC')], limit=1)
        if not product_normal_ot:
            raise ValidationError(_('service type product with internal reference SOC not found please create one.'))
        if not product_special_ot:
            raise ValidationError(_('service type product with internal reference NOC not found please create one.'))
        partner_dict = {}
        for task in task_ids:
            if task.partner_id not in partner_dict:
                partner_dict[task.partner_id] = task
            else:
                partner_dict[task.partner_id] |= task
        for partner, task in partner_dict.items():
            invoice_line_list = []
            filter_overtime_ids = task.mapped('overtime_lines_ids').filtered(lambda x: not x.invoiced)
            if filter_overtime_ids:
                special_overtime_line = filter_overtime_ids.filtered(lambda x: x.ot_type.code != 'NOD')
                normal_overtime_line = filter_overtime_ids - special_overtime_line
                normal_overtime_qty = sum(normal_overtime_line.mapped('ot_hour'))
                special_overtime_qty = sum(special_overtime_line.mapped('ot_hour'))
                if normal_overtime_line and normal_overtime_qty > 0:
                    vals = (0, 0, {
                        'name': product_normal_ot.name,
                        'product_id': product_normal_ot.id,
                        'price_unit': product_normal_ot.lst_price,
                        'quantity': normal_overtime_qty
                    })
                    invoice_line_list.append(vals)
                if special_overtime_line and special_overtime_qty > 0:
                    valss = (0, 0, {
                        'name': product_special_ot.name,
                        'product_id': product_special_ot.id,
                        'price_unit': product_special_ot.lst_price,
                        'quantity': special_overtime_qty
                    })
                    invoice_line_list.append(valss)
                if normal_overtime_line or special_overtime_line:
                    invoice = self.env['account.move'].create({
                        'move_type': 'out_invoice',
                        'partner_id': partner.id,
                        'journal_id': self.journal_id.id,
                        'invoice_line_ids': invoice_line_list,
                        'invoice_date': date.today()
                    })
                if invoice:
                    task.overtime_lines_ids.write({'invoiced': True})
        return True



class TaskDemobilizeWizard(models.TransientModel):
    _name = "task.demobilize.wizard"
    _description="Task Demobilize Wizard"

    demobilize_date = fields.Date(string="Date", required=True)
    remark = fields.Text(string="Remark", required=True)
    emp_ids = fields.Many2many('hr.employee', string="Employee")


    @api.model
    def default_get(self, fields_list):
        res = super(TaskDemobilizeWizard, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            task_ids = self.env['project.task'].browse(active_ids)
            res['emp_ids'] = task_ids.resource_history_ids.mapped('employee_id').ids
        return res

    def task_emp_demobilize(self):
        task_ids = False
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            task_ids = self.env['project.task'].browse(active_ids)
        for task_demobilize in self:
            for emp_id in task_demobilize.emp_ids:
                resource_id = task_ids.resource_history_ids.filtered(lambda sol: sol.employee_id.id == emp_id.id)
                resource_id.write({'demobilize_date' : task_demobilize.demobilize_date, 'remarks': task_demobilize.remark})