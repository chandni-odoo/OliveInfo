from odoo import models, fields, api

class AvailableRoomReport(models.AbstractModel):
    _name = 'report.employee_accommodation.available_room_report_template'
    _description = 'Available Room Report'
    
    
    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env.company
        wizard = self.env['available.room.wizard'].browse(docids)
        camp_ids = data.get('camp_ids', [])

        # if not camp_ids:
        #     all_camps = self.env['accommodation.camp'].search([])
        # else:
        #     all_camps = self.env['accommodation.camp'].browse(camp_ids)

        domain = [('status', '=', 'active')]  
        if camp_ids:
            domain.append(('id', 'in', camp_ids)) 
        all_camps = self.env['accommodation.camp'].search(domain)

        camp_data = []
        for camp in all_camps:
            rooms = self.env['accommodation.room'].search([
                ('camp_id', '=', camp.id)
            ], order='floor_id, name')  

            room_data = [{
                'name': room.name or 'N/A',
                'floor': room.floor_id.name if room.floor_id else 'N/A',
                'type': room.type or 'N/A',
                'capacity': room.capacity or 0,
                'allocated_bed_count': room.allocated_bed_count or 0,
                'available_bed_count': room.available_bed_count or 0,
                'status': room.status or 'Unknown',
            } for room in rooms]

            if room_data:  
                camp_data.append({
                    'camp_name': camp.name,
                    'rooms': room_data,
                })

        return {
            'docs': camp_data,  
            'single_camp': len(camp_ids) == 1, 
            'company': company,
        }

    
    
    