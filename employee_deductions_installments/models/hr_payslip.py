from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'
    
    deduction_installment_id = fields.Many2one(
        'hr.employee.deduction.installment',
        string="Deduction Installment"
    )

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_deduction_inputs(self):
        """Get all deduction inputs for this payslip period"""
        self.ensure_one()
        inputs = []
        
        deductions = self.env['hr.employee.deduction'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'approved'),
        ])
        
        for deduction in deductions:
            installments = deduction.installment_ids.filtered(
                lambda inst: inst.state == 'draft' and 
                           inst.due_date >= self.date_from and 
                           inst.due_date <= self.date_to
            )
            
            for installment in installments:
                inputs.append({
                    'code': deduction.deduction_type_id.code,
                    # 'amount': installment.amount,
                    'amount': -abs(installment.amount),
                    'name': f"{deduction.name} - {installment.due_date}",
                    'deduction_installment_id': installment.id,
                    'description': deduction.deduction_type_id.name,
                })
        
        return inputs
    
    def compute_sheet(self):
        """Override compute_sheet to add deduction inputs"""
        for payslip in self:
            existing_deduction_inputs = payslip.input_line_ids.filtered(
                lambda x: x.deduction_installment_id
            )
            if existing_deduction_inputs:
                existing_deduction_inputs.unlink()
            
            deduction_inputs = payslip._get_deduction_inputs()
            
            for input_data in deduction_inputs:
                input_type = self.env['hr.payslip.input.type'].search([('code', '=', input_data['code'])], limit=1)
                if not input_type:
                    input_type = self.env['hr.payslip.input.type'].create({
                        'name': input_data['description'],
                        'code': input_data['code'],
                    })
                
                self.env['hr.payslip.input'].create({
                    'payslip_id': payslip.id,
                    'input_type_id': input_type.id,
                    'amount': input_data['amount'],
                    'name': input_data['description'],
                    'deduction_installment_id': input_data['deduction_installment_id'],
                })
        
        # return super(HrPayslip, self).compute_sheet()
        res = super(HrPayslip, self).compute_sheet()
        
        for payslip in self:
            payslip._update_line_names_with_rule_names()
        
        return res
    
    def _update_line_names_with_rule_names(self):
        """Update payslip line names with corresponding deduction type names (only for deductions)"""
        self.ensure_one()
        
        deduction_codes = self.input_line_ids.filtered(
            lambda x: x.deduction_installment_id
        ).mapped('code')
        
        for line in self.line_ids:
            if line.code in deduction_codes:
                input_line = self.input_line_ids.filtered(
                    lambda x: x.code == line.code and 
                            x.deduction_installment_id and
                            x.amount == line.amount
                )
                if input_line:
                    line.name = input_line[0].deduction_installment_id.deduction_id.deduction_type_id.name
    
    # def _update_line_names_with_rule_names(self):
    #     """Update payslip line names with corresponding salary rule names"""
    #     self.ensure_one()
        
    #     for line in self.line_ids:
    #         if line.salary_rule_id and line.salary_rule_id.name:
    #             line.name = line.salary_rule_id.name

    

    def action_payslip_done(self):
        """Mark installments as paid when payslip is confirmed"""
        res = super(HrPayslip, self).action_payslip_done()
        
        for payslip in self:
            for input_line in payslip.input_line_ids.filtered(
                lambda x: x.deduction_installment_id
            ):
                input_line.deduction_installment_id.mark_as_paid(payslip.id)
        
        return res

    def action_payslip_cancel(self):
        """Reset installments to draft when payslip is cancelled"""
        res = super(HrPayslip, self).action_payslip_cancel()
        
        for payslip in self:
            installments = payslip.input_line_ids.mapped('deduction_installment_id')
            installments.write({
                'state': 'draft',
                'payslip_id': False
            })
        
        return res

