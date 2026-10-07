# -*- coding: utf-8 -*-
from odoo import api, fields, models,_

class Driver(models.Model):
    _inherit = 'res.partner'

    nature_driver = fields.Selection([
        ('driver','Driver'),
        ('turnboy','Turn Boy'),
        ], string="Type Of")
    id_no = fields.Char('ID No')
    license_no = fields.Char('License No')  
    vehicle_reg = fields.Char('Vehicle Reg')
    location  = fields.Char('Location')  
    discplinary = fields.Char('Discplinary Record') 
    date_joining = fields.Date('Date of Joining')
    date_exit = fields.Date('Date of exit')  
    remarks= fields.Text('Remarks')

    def get_map_url(self):
        self.ensure_one()
        url = 'https://www.google.com/maps/dir/?api=1&destination={},{}'.format(self.partner_latitude,self.partner_longitude)
        return url

    def map_redirection(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': self.get_map_url(),
        }
