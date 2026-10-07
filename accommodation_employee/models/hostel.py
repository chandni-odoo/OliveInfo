# See LICENSE file for full copyright and licensing details.

from datetime import datetime

from dateutil.relativedelta import relativedelta as rd

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_hostel_rector = fields.Boolean("Building Supervisor",
        help="Activate if the following person is Building Supervisor")

class Accommodation(models.Model):
    _name = "accommodation"
    _description = "Information of type of accommodation"

    name = fields.Char("Accommodation Name", required=True, help="Name of Accommodation")
    student_ids = fields.One2many("building.type", "accommodation_id",
        string="building", help="Enter Building")
    employee_id = fields.Many2one("hr.employee", "Employee", help="Select Employee")

class HostelType(models.Model):
    _name = "building.type"
    _description = "Information of type of Building"

    name = fields.Char("Building Name", required=True, help="Name of Building")
    type = fields.Selection([("male", "Boys"), ("female", "Girls"),
        ("common", "Common")], "Building Type", help="Type of Building",
        required=True, default="common")
    other_info = fields.Text("Other Information",
        help="Enter more information")
    rector = fields.Many2one("res.partner", "Rector",
        help="Select Building rector")
    room_ids = fields.One2many("hostel.room", "name", "Room",
        help="Enter Building rooms")
    student_ids = fields.One2many("accommodation.employee", "hostel_info_id",
        string="Employee", help="Enter Employee")
    accommodation_id = fields.Many2one("accommodation", "Accommodation", help="Select Accommodation")

    @api.model
    def _search(self, args, offset=0, limit=None, order=None,
        count=False, access_rights_uid=None,):
        """Override method to get hostel of student selected"""
        if self._context.get("student_id"):
            stud_obj = self.env["student.student"]
            stud = stud_obj.browse(self._context["student_id"])
            datas = []
            if stud.gender:
                self._cr.execute(
"""select id from hostel_type where type=%s or type='common' """,
                    (stud.gender,),)
                data = self._cr.fetchall()
                for d in data:
                    datas.append(d[0])
            args.append(("id", "in", datas))
        return super(HostelType, self)._search(args=args,
            offset=offset, limit=limit, order=order,
            count=count, access_rights_uid=access_rights_uid,)

             


class HostelBlocks(models.Model):
    _name = "hostel.blocks"
    _description = "Building Blocks Information"
    _rec_name = "room_no"

    name = fields.Many2one("building.type", "Building", help="Name of Building")
    floor_no = fields.Integer("Floor No.", default=1, help="Floor Number")
    room_no = fields.Char("Room No.", required=True)



class HostelRoom(models.Model):

    _name = "hostel.room"
    _description = "Building Room Information"
    _rec_name = "room_no"

    @api.depends("student_per_room", "student_ids")
    def _compute_check_availability(self):
        """Method to check room availability"""
        for rec in self:
            rec.availability = rec.student_per_room - len(rec.student_ids.ids)

    @api.depends('student_per_room')
    def _compute_bed_count(self):
        self.bed_count = len(self.bed_ids.ids)

    @api.onchange("student_per_room")
    def onchnage_student_per_room(self):
        if self.student_per_room > 0:
            n = self.student_per_room
            for bed in range(0, n):
                self.env['room.bed'].create({'room_id': self.id})

    name = fields.Many2one("building.type", "Building", help="Name of Building")
    floor_no = fields.Integer("Floor No.", default=1, help="Floor Number")
    room_no = fields.Char("Room No.", required=True)
    bed_count = fields.Char("Bed", compute="_compute_bed_count")
    room_size = fields.Char("Room size.")
    student_per_room = fields.Integer("Employee Per Room", required=True,
        help="Employee allocated per room")
    availability = fields.Float(compute="_compute_check_availability",
        store=True, string="Availability", help="Room availability in Building")
    rent_amount = fields.Float("Rent Amount Per Month",
        help="Enter rent amount per month")
    hostel_amenities_ids = fields.Many2many("hostel.amenities",
        "hostel_room_amenities_rel", "account_id", "tax_id",
        string="Building Amenities", domain="[('active', '=', True)]",
        help="Select Building roon amenities")
    student_ids = fields.One2many("accommodation.employee", "room_id",
        string="Employees", help="Enter Employees")
    bed_ids = fields.One2many("room.bed", "room_id",
        string="Bed", help="Select Bed")
    equipment_emp_id = fields.Many2one("maintenance.equipment", "Equipment", help="Select Equipment")
    equip_ids = fields.One2many("maintenance.equipment", "equipment_name_id",
        string="Equipment", help="Enter Equipment")

    _sql_constraints = [
        ("room_no_unique", "unique(room_no)", "Room number must be unique!"),
        ("floor_per_hostel", "check(floor_no < 99)",
            "Error ! Floor per Building should be less than 99."),
        ("student_per_room_greater", "check(student_per_room < 10)",
            "Error ! Employee per room should be less than 10.")]

    @api.constrains("rent_amount")
    def _check_rent_amount(self):
        """Constraint on negative rent amount"""
        if self.rent_amount < 0:
            raise ValidationError(_(
"Rent Amount Per Month should not be a negative value!"))


    def action_view_bed_count(self):
        return {
            'name': 'Room Bed',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'room.bed',
        }

class Roombed(models.Model):
    _name = "room.bed"
    _description = "Building Bed Information"

    name = fields.Char("Sequence")
    room_id = fields.Many2one("hostel.room", "Room",
        help="Select Building room")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('room.bed') or _('New')
        return super(Roombed, self).create(vals)










class AccommodationEmployee(models.Model):
    _name = "accommodation.employee"
    _description = "Accommodation Employee Information"
    _rec_name = "employee_id"

    @api.depends("room_rent", "paid_amount")
    def _compute_remaining_fee_amt(self):
        """Method to compute hostel amount"""
        for rec in self:
            rec.remaining_amount = rec.room_rent - (rec.paid_amount or 0.0)

    def _compute_invoices(self):
        """Method to compute number of invoice of student"""
        inv_obj = self.env["account.move"]
        for rec in self:
            rec.compute_inv = inv_obj.search_count(
                [("accommodation_employee_id", "=", rec.id)])

    @api.depends("duration")
    def _compute_rent(self):
        """Method to compute hostel room rent"""
        for rec in self:
            rec.room_rent = rec.duration * rec.room_id.rent_amount

    @api.depends("status")
    def _get_hostel_user(self):
        user_group = self.env.ref("accommodation_employee.group_hostel_user")
        if user_group.id in [group.id for group in self.env.user.groups_id]:
            self.hostel_user = True

    hostel_id = fields.Char("Building ID", readonly=True,
        help="Enter Building ID", default=lambda self: _("New"))
    compute_inv = fields.Integer("Number of invoice",
        compute="_compute_invoices", help="No of invoice of related employee")
    student_id = fields.Many2one("student.student", "Employee",
        help="Select employee")
    school_id = fields.Many2one("school.school", "School",
        help="Select school")
    room_rent = fields.Float("Total Room Rent", compute="_compute_rent",
        required=True, help="Rent of room")
    admission_date = fields.Datetime("Admission Date",
        help="Date of admission in Building",
        default=fields.Datetime.now)
    discharge_date = fields.Datetime("Discharge Date",
        help="Date on which employee discharge")
    paid_amount = fields.Float("Paid Amount", help="Amount Paid")
    hostel_info_id = fields.Many2one(
        "building.type", "Building", help="Select Building type"
    )
    room_id = fields.Many2one("hostel.room", "Room",
        help="Select Building room")
    duration = fields.Integer("Duration", help="Enter duration of living")
    rent_pay = fields.Float("Rent", help="Enter rent pay of the Building")
    acutal_discharge_date = fields.Datetime("Actual Discharge Date",
        help="Date on which employee discharge")
    remaining_amount = fields.Float(compute="_compute_remaining_fee_amt",
        string="Remaining Amount")
    status = fields.Selection([("draft", "Draft"),
        ("reservation", "Reservation"), ("pending", "Pending"),
        ("paid", "Done"),("discharge", "Discharge"), ("cancel", "Cancel")],
        string="Status", copy=False, default="draft",
        help="State of the employee Building")
    hostel_types = fields.Char("Type", help="Enter Building type")
    stud_gender = fields.Char("Gender", help="Employee Gender")
    active = fields.Boolean("Active", default=True,
        help="Activate/Deactivate Building record")
    employee_id = fields.Many2one("hr.employee", "Employee", help="Select employee")
    accommodation_id = fields.Many2one("accommodation", "Accommodation", help="Select Accommodation", related="hostel_info_id.accommodation_id")

    name = fields.Char()
    emp_no = fields.Char()
    country_id = fields.Many2one('res.country')
    date_started = fields.Date()
    departure_date = fields.Date()
    hr_employee_type = fields.Selection([('own', 'Own'),('subcontractor','Subcontractor')], default='own', required=True)

    # _sql_constraints = [("admission_date_greater",
    #     "check(discharge_date >= admission_date)",
    #     "Error ! Discharge Date cannot be set" "before Admission Date!")]

    @api.constrains("duration")
    def check_duration(self):
        """Method to check duration should be greater than zero"""
        if self.duration <= 0:
            raise ValidationError(_("Duration should be greater than 0!"))

    @api.constrains("room_id")
    def check_room_avaliable(self):
        """Check Room Availability"""
        if self.room_id.availability <= 0:
            raise ValidationError(_(
                "There is no availability in the room!"))

    @api.onchange("hostel_info_id")
    def onchange_hostel_types(self):
        """Onchange method for hostel type"""
        self.hostel_types = self.hostel_info_id.type

    @api.onchange("student_id")
    def onchange_student_gender(self):
        """Method to get gender of student"""
        self.stud_gender = self.student_id.gender

    @api.onchange("hostel_info_id")
    def onchange_hostel(self):
        """Method to make room false when hostel changes"""
        self.room_id = False

    def cancel_state(self):
        """Method to change state to cancel"""
        for rec in self:
            rec.status = "cancel"
            # increase room availability
            rec.room_id.availability += 1

    def reservation_state(self):
        """Method to change state to reservation"""
        sequence_obj = self.env["ir.sequence"]
        for rec in self:
            if rec.hostel_id == "New":
                rec.hostel_id = sequence_obj.next_by_code(
                    "accommodation.employee") or _("New")
            rec.status = "reservation"

    @api.onchange("admission_date", "duration")
    def onchnage_discharge_date(self):
        """To calculate discharge date based on current date and duration"""
        if self.admission_date:
            self.discharge_date = self.admission_date + rd(months=self.duration
                )

    @api.model
    def create(self, vals):
        """This method is to set Discharge Date according to values added in
        admission date or duration fields."""
        res = super(AccommodationEmployee, self).create(vals)
        res.discharge_date = res.admission_date + rd(months=res.duration)
        return res

    def write(self, vals):
        """This method is to set Discharge Date according to changes in.

        admission date or duration fields.
        """
        addmissiondate = self.admission_date
        if vals.get("admission_date"):
            addmissiondate = datetime.strptime(
                vals.get("admission_date"), DEFAULT_SERVER_DATETIME_FORMAT)
        if vals.get("admission_date") or vals.get("duration"):
            duration_months = vals.get("duration") or self.duration
            discharge_date = addmissiondate + rd(months=duration_months)
            vals.update({"discharge_date": discharge_date})
        return super(AccommodationEmployee, self).write(vals)

    def unlink(self):
        """Inherited unlink method to make check state at record deletion"""
        status_list = ["reservation", "pending", "paid"]
        for rec in self:
            if rec.status in status_list:
                raise ValidationError(_(
                    "You can delete record in unconfirmed state!"))
        return super(AccommodationEmployee, self).unlink()

    # @api.constrains("student_id")
    # def check_student_registration(self):
    #     """Constraint to check student record duplication in hostel"""
    #     if self.search([
    #             ("student_id", "=", self.student_id.id),
    #             ("status", "not in", ["cancel", "discharge"]),
    #             ("id", "not in", self.ids)]):
    #         raise ValidationError(_(
    #             "Selected employee is already registered!"))

    def discharge_state(self):
        """Method to change state to discharge"""
        for rec in self:
            rec.status = "discharge"
            rec.room_id.availability += 1
            # set discharge date equal to current date
            rec.acutal_discharge_date = fields.datetime.today()

    def student_expire(self):
        """ Schedular to discharge student from hostel"""
        current_date = fields.datetime.today()
        for student in self.env["accommodation.employee"].search(
                [("discharge_date", "<", current_date),
                ("status", "!=", "draft")]):
            student.discharge_state()

    def invoice_view(self):
        """Method to view number of invoice of student"""
        invoice_obj = self.env["account.move"]
        for rec in self:
            invoices_rec = invoice_obj.search([("accommodation_employee_id", "=",
                                                rec.id)])
            action = rec.env.ref("account.action_move_out_invoice_type"
                ).read()[0]
            if len(invoices_rec) > 1:
                action["domain"] = [("id", "in", invoices_rec.ids)]
            elif len(invoices_rec) == 1:
                action["views"] = [
                    (rec.env.ref("account.view_move_form").id, "form")]
                action["res_id"] = invoices_rec.ids[0]
            else:
                action = {"type": "ir.actions.act_window_close"}
        return action

    def pay_fees(self):
        """Method generate invoice of hostel fees of student"""
        invoice_obj = self.env["account.move"]
        for rec in self:
            rec.write({"status": "pending"})
            partner = rec.student_id and rec.student_id.partner_id
            vals = {"partner_id": partner.id,
                    "move_type": "out_invoice",
                    "accommodation_employee_id": rec.id,
                    "hostel_ref": rec.hostel_id}
            account_inv_id = invoice_obj.create(vals)
            acc_id = account_inv_id.journal_id.default_account_id.id
            account_view_id = rec.env.ref("account.view_move_form")
            for _move_line in account_inv_id:
                account_inv_id.write({"invoice_line_ids": [(0, 0, {
                    "name": rec.hostel_info_id.name,
                    "account_id": acc_id,
                    "quantity": rec.duration,
                    "price_unit": rec.room_id.rent_amount,
                })]})
            return {
                "name": _("Pay Building Fees"),
                "view_mode": "form",
                "res_model": "account.move",
                "view_id": account_view_id.id,
                "type": "ir.actions.act_window",
                "nodestroy": True,
                "target": "current",
                "res_id": account_inv_id.id,
                "context": {},
            }

    def print_fee_receipt(self):
        """Method to print fee reciept"""
        return self.env.ref("school_hostel.report_hostel_fee_reciept_qweb"
            ).report_action(self)


class HostelAmenities(models.Model):
    _name = "hostel.amenities"

    name = fields.Char("Name", help="Provided Building Amenity")
    active = fields.Boolean("Active",
        help="Activate/Deactivate whether the amenity should be given or not")


class AccountMove(models.Model):

    _inherit = "account.move"

    accommodation_employee_id = fields.Many2one("accommodation.employee",
        string="Hostel Student", help="Select hostel student")
    hostel_ref = fields.Char("Hostel Fees Reference",
        help="Hostel Fee Reference")


# class AccountPaymentRegister(models.TransientModel):
#     _inherit = "account.payment.register"

#     def action_create_payments(self):
#         """
#             Override method to write paid amount in hostel student
#         """
#         res = super(AccountPaymentRegister, self).action_create_payments()
#         inv = False
#         for rec in self:
#             if self._context.get('active_model') == 'account.move':
#                 inv = self.env['account.move'].browse(self._context.get('active_ids', []))
#             vals = {}
#             if inv.accommodation_employee_id and inv.payment_state == "paid":
#                 fees_payment = inv.accommodation_employee_id.paid_amount + rec.amount
#                 vals.update({"status": "paid", "paid_amount": fees_payment})
#                 inv.accommodation_employee_id.write(vals)
#             elif inv.accommodation_employee_id and inv.payment_state == "not_paid":
#                 fees_payment = inv.accommodation_employee_id.paid_amount + rec.amount
#                 vals.update({
#                     "status": "pending",
#                     "paid_amount": fees_payment,
#                     "remaining_amount": inv.amount_residual})
#             inv.accommodation_employee_id.write(vals)
#         return res


class Employee(models.Model):
    _inherit = "hr.employee"


    # hostel_info_id = fields.Many2one(
    #     "building.type", "Building", help="Select Building type"
    # )
    # room_id = fields.Many2one("hostel.room", "Room",
    #     help="Select Building room")
    # accommodation_id = fields.Many2one("accommodation", "Accommodation",
    #     help="Select Accommodation")

    accommodation_emp_ids = fields.One2many("accommodation.employee", "employee_id",
        string="Accommodation", help="Enter Accommodation")

    # admission_date = fields.Datetime("Admission Date",
    #     help="Date of admission in Building",
    #     default=fields.Datetime.now)
    # discharge_date = fields.Datetime("Discharge Date",
    #     help="Date of Discharge in Building",
    #     default=fields.Datetime.now)

class AccommodationEquipment(models.Model):
    _name = "accommodation.equipment"
    _description = "Accommodation Equipment Information"
    _rec_name = "equipment_id"


    equipment_id = fields.Many2one("maintenance.equipment", "Equipment", help="Select Equipment")
    


class Equipment(models.Model):
    _inherit = "maintenance.equipment"


    accommodation_equipment_ids = fields.One2many("hostel.room", "equipment_emp_id", 
        string="Accommodation Equipment", help="Enter Accommodation Equipment")
    equipment_name_id = fields.Many2one("hostel.room", "HostelRoom", help="Select Equipment")


class EmployeeTransfer(models.Model):
    _name = 'employee.transfer'
    _description = 'Employee Transfer'


    employee_transfer_id = fields.Many2one("accommodation.employee", "Employee", help="Select Employee")
    current_building_id = fields.Many2one("building.type",string="Current Building", related='employee_transfer_id.hostel_info_id')
    new_building_id = fields.Many2one("building.type", "New Building")




