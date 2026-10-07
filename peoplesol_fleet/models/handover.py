# -*- coding: utf-8 -*-

from odoo import api, fields, models,_

selection_type = [('Satisfactory', '✔'),('Defective/Missing', '✕'),('Not Applicable','N/A')]

class VehicleHandover(models.Model):
    _name = 'vehicle.handover'
    
    name = fields.Char(string='Name', copy= False, readonly= True)
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, store=True, tracking= True)
    issue_no = fields.Integer('Issue No')
    issue_date = fields.Datetime(default=lambda self: fields.Datetime.now())
    date = fields.Date('Date')
    driver_id = fields.Many2one('res.partner', 'Assign')
    signature = fields.Binary('Signature')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle Registration')
    engine_oil = fields.Selection(selection_type, string="Engine Oil")
    indicators = fields.Selection(selection_type, string="Indicators")
    door_wing_mirrors = fields.Selection(selection_type, string="Door/Wing Mirrors")
    seat_belts = fields.Selection(selection_type, string="Seat Belts")
    brake = fields.Selection(selection_type, string="Brake")
    side_lights = fields.Selection(selection_type, string="Side Lights")
    wiper_blades = fields.Selection(selection_type, string="Wiper Blades")
    first_aid_kit = fields.Selection(selection_type, string="First Aid kit")
    clutch = fields.Selection(selection_type, string="Clutch")
    headlights_dipped = fields.Selection(selection_type, string="Headlights (Dipped)")
    screen_washers = fields.Selection(selection_type, string="Screen Washers")
    fire_extinguisher = fields.Selection(selection_type, string="Fire Extinguisher")
    power_steering = fields.Selection(selection_type, string="Power Steering")
    headlights_mains = fields.Selection(selection_type, string="Headlights (Main)")
    tyre_pressure = fields.Selection(selection_type, string="Tyre Pressure")
    head_restraint_adjustment = fields.Selection(selection_type, string="Head Restraint Adjustment")
    auto_transmission = fields.Selection(selection_type, string="Auto Transmission")
    number_plate= fields.Selection(selection_type, string="Number Plate")
    tyre_wear= fields.Selection(selection_type, string="Tyre Wear")
    torch= fields.Selection(selection_type, string="Torch")
    screen_wash= fields.Selection(selection_type, string="Screen Wash")
    reversing= fields.Selection(selection_type, string="Reversing")
    tyre_damage= fields.Selection(selection_type, string="Tyre Damage")
    warning_triangle= fields.Selection(selection_type, string="Warning Triangle")
    fuel_min =fields.Selection(selection_type, string="Fuel (Min ¼ full)")
    warning_lights =fields.Selection(selection_type, string="Warning Lights")
    spare_wheel =fields.Selection(selection_type, string="Spare Wheel")
    general_bodywork =fields.Selection(selection_type, string="General Bodywork")
    coolant =fields.Selection(selection_type, string="Coolant")
    horn = fields.Selection(selection_type, string="Horn")
    cleanliness = fields.Selection(selection_type, string="Cleanliness of number plate, windows, lights")
    tool_box = fields.Selection(selection_type, string="Tool box")
    windscreen_wipers = fields.Selection(selection_type, string="Windscreen Wipers")
    general_external = fields.Selection(selection_type, string="General external condition of the vehicle.")
    general_interior = fields.Selection(selection_type, string="General interior with dashboard outlook.")
    battery = fields.Selection(selection_type, string="Battery")
    door_locking = fields.Selection(selection_type, string="Door Locking")
    comment = fields.Text('Damage noted, repairs due etcs Mark on diagram any damage and date noted')
    reason = fields.Text('Reason for handing over the vehicle')
    vehicle_handed_id = fields.Many2one('res.partner','Vehicle handed over to:')
    id_nos = fields.Char('ID No:')
    signature_2 = fields.Binary('Signature')
    signature_3 = fields.Binary('Signature')
    date_2 = fields.Date('Date')
    date_3 = fields.Date('Date')
    confirmed_id = fields.Many2one('res.partner', 'Confirmed by:')
    designed_id = fields.Many2one('res.partner','Designation:')
    image_front = fields.Image()
    image_rear = fields.Image()
    type_of_assignment = fields.Selection([('new','New'),('old','Old')],string="Assign Type", default="old", required=True)
    history_ids = fields.One2many('vehicle.history.line', 'history_id', string='History Lines')

    @api.model
    def create(self, values):
        if values.get('name', _('New')) == _('New'):
            values['name'] = self.env['ir.sequence'].next_by_code('vehicle.handover')
        return super(VehicleHandover, self).create(values)

    def update_driver(self):
        vals = {'type_of_assignment':'old'}
        if self.driver_id and self.vehicle_id and self.type_of_assignment =='new':
            self.vehicle_id.driver_id = self.driver_id.id
            vals.update({'type_of_assignment':'new'})

        vals.update({'date': fields.date.today(),
                  'driver_id': self.driver_id.id,
                  'vehicle_id': self.vehicle_id.id,
                  'history_id':self.id,
                  })
        self.env['vehicle.history.line'].create(vals)


class VehicleHistory(models.Model):
    _name = 'vehicle.history.line'
    _description = "Vehicle History"


    date = fields.Date('Date')
    driver_id = fields.Many2one('res.partner', string='Driver Name')
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    type_of_assignment = fields.Selection([('new','New'),('old','Old')],string="Assign Type")
    history_id = fields.Many2one('vehicle.handover', string="Handover")
