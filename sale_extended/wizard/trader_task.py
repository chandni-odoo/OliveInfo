# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TraderTaskWizard(models.TransientModel):
    _name = "trader.task.wizard"
    _description = "Trader Task Wizard"

    @api.model
    def _default_task(self):
        task_id = self.env['project.task'].browse(self.env.context.get('active_id'))
        return task_id.id

    @api.model
    def _default_sale_order(self):
        task_id = self.env['project.task'].browse(self.env.context.get('active_id'))
        return task_id.sale_order_id.id

    task_id = fields.Many2one('project.task', string='Task', default=_default_task, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    date = fields.Date(string='Date')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', default=_default_sale_order)
    status = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='Status')
    partner_id = fields.Many2one('res.partner', string='Customer')
    attachment_id = fields.Binary(string="Attachment")
    remark = fields.Text('Remark')
    employee_ids = fields.One2many('employee.wizard', 'trade_id')
    trade_test_ids = fields.Many2many('trade.test.record')

    def action_approve(self):
        for rec in self.trade_test_ids:
            if rec.status == 'pass':
                rec.employee_id.write({'product_ids': [(4, self.task_id.sale_line_id.product_id.id)]})
            vals = {
                'task_id': self.task_id.id,
                'employee_id': rec.employee_id.id,
                'status': rec.status,
                'date': self.date,
                'sale_order_id': self.sale_order_id.id,
            }
            trade_test_records = self.env['trade.test.record'].create(vals)


class EmployeeWizard(models.TransientModel):
    _name = "employee.wizard"
    _description = "Employee Wizard"

    employee_id = fields.Many2one('hr.employee', string='Employee')
    status = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='Status')
    trade_id = fields.Many2one('trader.task.wizard', string="Trade Test")
    attachment_id = fields.Binary(string="Attachment")
    remark = fields.Text('Remark')


class hrEmployee(models.Model):
    _inherit = "hr.employee"

    task_id = fields.Many2one('project.task', string='Task')

    # status = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='Status')
    # status = fields.Selection([('family', 'Family'), ('single', 'Singe')], string='Status')

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    trade_ids = fields.One2many('trader.task.wizard', 'employee_id')
    date = fields.Date(string='Date')
    trade_rec_ids = fields.One2many('trade.test.record', 'employee_id')


class TradeTestRecord(models.Model):
    _name = "trade.test.record"
    _description = "Trade Test Record"

    task_id = fields.Many2one('project.task', string='Task')
    status = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='Status')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    date = fields.Date(string='Date')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    attachment_id = fields.Binary(string="Attachment")
    remark = fields.Text('Remark')

    @api.onchange('status')
    def _onchange_status(self):
        if self.task_id and self.task_id.sale_line_id and self.task_id.sale_line_id.product_id and self.status == 'pass':
            self.employee_id.write({'product_ids': [(4, self.task_id.sale_line_id.product_id.id)]})
