from odoo import models, api

class AvailableBedsReport(models.AbstractModel):
    _name = 'report.employee_accommodation.available_beds_report_template'
    _description = 'Available Beds Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env.company
        wizard = self.env['available.beds.wizard'].browse(docids)
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
            available_beds = self.env['accommodation.bed'].search([
                ('status', '=', 'available'),
                ('camp_id', '=', camp.id),
            ], order='floor_id, room_id, name')  
            camp_data.append({
                'camp_name': camp.name,
                'beds': available_beds,
            })

        return {
            'docs': camp_data, 
            'company': company, 
            'single_camp': len(camp_ids) == 1, 
            
        }