# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from lxml import etree
import json


class ProjectTask(models.Model):
    _inherit = "project.task"

    # trade_task_ids = fields.One2many('trader.task.wizard', 'task_id')
    trade_task_count = fields.Integer(string='Trade Task', compute="_get_trade_test", store=False)
    frequency_id = fields.Many2one('so.frequency', string="Frequency")
    
    is_trade = fields.Boolean(related='sale_line_id.trade_test', string="Is Trade", store=True)
    #  source_id_domain = fields.Char(
    #     compute="_compute_source_id_domain",
    #     readonly=True,
    #     store=False,
    # )

    #  @api.depends('trade_task_count')
    #  def _compute_source_id_domain(self):
    #      for rec in self:
    #          domain = []
    #          trade_task_emp_ids = []
    #          if rec.trade_task_count > 0 and rec.trade_test:
    #              for trade_test_id in self.env['trade.test.record'].search([('task_id','=', rec.id),('status','=', 'pass')]):
    #                  trade_task_emp_ids.append(trade_test_id.employee_id.id)
    #              domain = [('id', 'in', trade_task_emp_ids),('emp_status', '=', 'active')]
    #          elif rec.trade_task_count == 0 and rec.trade_test:
    #              domain = [('id', 'in', [])]
    #          else:
    #              domain = [('id', 'in', rec.employee_ids.ids),('emp_status', '=', 'active')]
    #          rec.source_id_domain = json.dumps(
    #             domain
    #          )

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(ProjectTask, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    #     doc = etree.XML(res['arch'])
    #     for node in doc.xpath("//field[@name='resource_ids']"):
    #         context = self._context
    #         if context.get('search_default_sale_order_id'):
    #             current_record = context.get('task_id')
    #         else:        
    #             params = context.get('params')
    #             if params:
    #                 current_record = params.get('id')
    #         project_id = self.env['project.task'].browse(current_record)
    #         if project_id:
    #             modifiers = json.loads(node.get("modifiers"))
    #             trade_task_emp_ids = []
    #             if project_id.trade_task_count > 0 and project_id.trade_test:
    #                 for trade_test_id in self.env['trade.test.record'].search([('task_id','=', project_id.id),('status','=', 'pass')]):
    #                     trade_task_emp_ids.append(trade_test_id.employee_id.id)
    #                 domain = [('id', 'in', trade_task_emp_ids),('emp_status', '=', 'active')]
    #             elif project_id.trade_task_count == 0 and project_id.trade_test:
    #                 domain = [('id', 'in', [])]
    #             else:
    #                 domain = [('id', 'in', project_id.employee_ids.ids),('emp_status', '=', 'active')]
    #             node.set("domain", json.dumps(domain))
    #     res['arch'] = etree.tostring(doc)
    #     return res

    @api.depends('parent_id')
    def _get_trade_test(self):
        for rec in self:
            trade_test = self.env['trade.test.record'].search([('task_id', '=', rec.id)])
            if trade_test:
                rec.trade_task_count = len(trade_test)
            else:
                rec.trade_task_count = 0

    def action_view_trade_task(self):
        print('View Trade TaskView Trade TaskView Trade TaskView Trade TaskView Trade Task')
        view_id = self.env.ref("sale_extended.trade_test_record_tree_view")
        domain = [("task_id", 'in', self.ids)]
        return {
            'name': 'Trade Test',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'trade.test.record',
            'view_id': view_id.id,
            'domain': domain,
        }

    def action_trade_test(self):
        print('Trade TestTrade TestTrade TestTrade TestTrade TestTrade TestTrade Test')
        view_id = self.env.ref("sale_extended.trader_task_wizard_form_view")
        return {
            'name': 'Trade Test',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': view_id.id,
            'res_model': 'trader.task.wizard',
            'target': 'new',
        }


