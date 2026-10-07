from odoo import models, fields, api

class OccupancyReport(models.AbstractModel):
    _name = 'report.employee_accommodation.occupancy_report_template'
    _description = 'Occupancy List Report'
    
    
    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env.company
        
        to_date = data.get('to_date')
        camp_ids = data.get('camp_ids', [])
        floor_ids = data.get('floor_ids', [])
        room_ids = data.get('room_ids', [])

        if isinstance(to_date, str):
            to_date = fields.Date.from_string(to_date)
        
        formatted_date = to_date.strftime('%d-%m-%Y') if to_date else ''

        domain = [
            ('check_in_date', '<=', to_date),
            ('status', '=', 'checked_in'),
            ('camp_id.status', '=', 'active')
        ]
        if camp_ids:
            domain.append(('camp_id', 'in', camp_ids))
        
        if floor_ids:
            domain.append(('floor_id', 'in', floor_ids))
        
        if room_ids:
            domain.append(('room_id', 'in', room_ids))
        
        docs = self.env['accommodation.check.in'].search(domain)
        
        camps_data = {}
        for doc in docs:
            camp_id = doc.camp_id.id
            if camp_id not in camps_data:
                camps_data[camp_id] = {
                    'camp_name': doc.camp_id.name,
                    'docs': [],
                    'total_occupied_beds': 0,
                }
            camps_data[camp_id]['docs'].append(doc)
            camps_data[camp_id]['total_occupied_beds'] += 1
        
        return {
            'camps_data': list(camps_data.values()),
            'to_date': formatted_date, 
            'company': company,
        }
        


    



