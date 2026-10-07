from odoo import api, models

class RoomSummaryReport(models.AbstractModel):
    _name = 'report.employee_accommodation.room_summary_report'
    _description = "Room Summary Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env.company
        domain = [('camp_id.status', '=', 'active')]
        if data and data.get('camp_ids'):
            domain.append(('camp_id', 'in', data['camp_ids']))
        
        rooms = self.env['accommodation.room'].search(domain)
        
        grouped_rooms = {}
        for room in rooms:
            camp_id = room.camp_id.id
            if camp_id not in grouped_rooms:
                grouped_rooms[camp_id] = {
                    'camp_name': room.camp_id.name,
                    'rooms': [],
                    'total_capacity': 0,
                    'total_available_beds': 0,
                    'total_allocated_beds': 0,
                }
            grouped_rooms[camp_id]['rooms'].append(room)
            grouped_rooms[camp_id]['total_capacity'] += room.capacity
            grouped_rooms[camp_id]['total_available_beds'] += room.available_bed_count
            grouped_rooms[camp_id]['total_allocated_beds'] += room.allocated_bed_count

        grouped_rooms_list = list(grouped_rooms.values())

        return {
            'grouped_rooms': grouped_rooms_list,
            'company': company,
        }
