# See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import common


class TestHostel(common.TransactionCase):
    def setUp(self):
        super(TestHostel, self).setUp()
        self.hostel_type_obj = self.env["building.type"]
        self.hostel_room_obj = self.env["building.room"]
        self.accommodation_employee_obj = self.env["accommodation.employee"]
        self.student = self.env.ref("school.demo_student_student_7")
        self.res_partner = self.env["res.partner"]
        # create hostel rector
        self.rector = self.res_partner.create(
            {
                "name": "Hostel Rector",
                "is_hostel_rector": True,
                "email": "hostelrec@demo.com",
            }
        )
        #        Create Hostel Type
        self.hostel_type = self.hostel_type_obj.create(
            {"name": "Test Hostel", "type": "female", "rector": self.rector.id}
        )
        #        Create Hostel Room
        self.hostel_room = self.hostel_room_obj.create(
            {
                "name": self.hostel_type.id,
                "room_no": "101",
                "student_per_room": "3",
                "rent_amount": 1000,
                "telephone": True,
                "ac": True,
                "private_bathroom": True,
            }
        )
        self.hostel_room._compute_check_availability()
        #        Create Hostel Student
        current_date = fields.datetime.today()
        self.accommodation_employee = self.accommodation_employee_obj.create(
            {
                "student_id": self.student.id,
                "hostel_info_id": self.hostel_type.id,
                "room_id": self.hostel_room.id,
                "admission_date": current_date,
                "duration": 2,
            }
        )
        self.accommodation_employee.check_duration()
        self.accommodation_employee._compute_remaining_fee_amt()
        self.accommodation_employee._compute_rent()
        self.accommodation_employee._get_hostel_user()
        self.accommodation_employee.reservation_state()
        self.accommodation_employee.onchnage_discharge_date()
        self.accommodation_employee.discharge_state()
        self.accommodation_employee.student_expire()
        self.accommodation_employee.print_fee_receipt()

    def test_hostel(self):
        self.assertEqual(self.student.state, "done")
        self.assertIn(self.hostel_room.name, self.hostel_type)
