# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class SaleOrder(models.Model):
	_inherit = "sale.order"

	state = fields.Selection(selection_add=[('revisions', 'REVISIONS')])
	version = fields.Float(string="Version", default=1.0, readonly=True, digits=(12,1))
	version_date = fields.Date(string="Version Date")
	sale_order_id =  fields.Many2one('sale.order', string="Old Version", readonly=True)
	version_count = fields.Integer(string="Version", compute="_compute_version_count")
	active = fields.Boolean(string="Active", default=True)

	def action_quotation_version(self):
		if self.state in ["draft", 'sent']:
			sale_ids = self.env['sale.order'].search([('active', '=', False), ('name', '=', self.name)]) | self
			version = self.version
			if sale_ids:
				version = max(sale_ids.mapped('version'))
				version = version + 0.1
			else:
				version = version + 0.1
			sale_record = self.copy({'name': self.name, 'active': False})
			sale_record.write({'state' : 'revisions','version_date' : fields.Date.today()})
			sale_order_id = self.env['sale.order'].search(
				[('name', '=', self.name),('active' , '=', False)], limit=1)
			self.version = version
			self.write({
				'sale_order_id' : sale_order_id.id, 
				'version_date' : fields.Date.today(),
				'state' : 'costing',
				})

	def get_version(self):
		self.ensure_one()
		return {
			'type': 'ir.actions.act_window',
			'name': 'Version',
			'view_type': 'form',
			'res_model': 'sale.order',
			'view_id': False,
			'view_mode': 'tree,form',
			'domain': [('name', '=', self.name), ('active' , '=', False)]
		}

	def _compute_version_count(self):
		for record in self:
			record.version_count = self.env['sale.order'].search_count(
				[('name', '=', self.name),('active' , '=', False)])

	def action_restore(self):
		sale_id = self.env['sale.order'].search([('name', '=', self.name), ('active' , '=', True)],limit=1)
		self.active = True
		self.state = "costing"
		sale_id.active = False
		sale_id.state = "revisions"
		sale_id.sale_order_id = self.id
