# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ContactsLocation(models.Model):
    _name = 'contact.location'
    
    name = fields.Char("Contact Location")
    latitude = fields.Char('Location Latitude')
    longitude = fields.Char('Location Longitude')

    