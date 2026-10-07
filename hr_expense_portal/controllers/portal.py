import json
from odoo import fields, http, _
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.payment import utils as payment_utils
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager, get_records_pager
from datetime import datetime
import operator
import base64

# class Segment(http.Controller):

#     @http.route(['/segment'], type='http', auth='public', website=True)
#     def VanPay(self):
#         print("CALLLLLLLLLLLLLLLL")
#         return request.render("hr_expense_portal.website_van_pay")

#     @http.route('/add/payment', type='json', auth='public')
#     def create_payment(self, data):
#         import requests
#         x = requests.get('https://w3schools.com')
#         return x.text


class CustomerPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        employee_id = request.env.user.employee_id
        if 'expense_count' in counters:
            expense_count = request.env['hr.expense'].sudo().search_count([('employee_id', '=', employee_id.id)]) \
                if request.env['hr.expense'].check_access_rights('read', raise_exception=False) else 0
            values['expense_count'] = expense_count
        return values

    @http.route(['/website_expense_form'], type='http', auth="public", website=True)
    def create_expense(self, **post):
        data = post
        product_id = request.env['product.product'].sudo().browse(int(data.get('category_id')))
        employee_id = request.env.user.employee_id
        company_id = request.env.user.company_id
        expense_date = fields.Date.from_string(data.get('expense_date'))
        file = post.get('myexpencefile')
        account = request.env['ir.property'].sudo().with_company(company_id).sudo()._get('property_account_expense_categ_id', 'product.category')
        vals = {
            'extract_state': 'no_extract_requested',
            'extract_status_code': 0,
            'employee_id' : employee_id.id or False, 
            'product_id' : product_id.id or False, 
            'date' : expense_date,
            'payment_mode' : 'own_account' if data.get('paid_by') == 'employee' else 'company_account',
            'unit_amount' : float(data.get('expense_amount', 0.0)),
            'currency_id' : int(data.get('currency_id'), False),
            'quantity' : float(data.get('expense_quantity', 0.0)),
            'product_uom_id' : product_id.uom_id.id if product_id.uom_id else False,
            'state' : 'draft',
            'name' : data.get('description_expance', ''),
            'account_id' : account.id or False
        }
        request_id = request.env['hr.expense'].sudo().create(vals)
        attachment = request.env['ir.attachment'].sudo().create({
                'type': 'binary',
                'name': data.get('description_expance', ''),
                'res_model': 'hr.expense',
                'datas': base64.b64encode(file.read()),
                'res_id' : request_id.id
            })
        return request.redirect('/my/home')

    def _get_expence_category(self):
        expensed_ids = request.env['product.product'].sudo().search([('can_be_expensed', '=', True)])
        return expensed_ids

    def _get_expence_currency(self):
        currency_ids = request.env['res.currency'].sudo().search([])
        return currency_ids

    @http.route(['/my/expense', '/my/request/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_expense(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        employee_id = request.env.user.employee_id
        expense_obj = request.env['hr.expense']
        domain = [
            ('employee_id', '=', employee_id.id if employee_id else False)
        ]
        searchbar_sortings = {
            'state': {'label': _('state'), 'order': 'state desc'},
           
        }
        # default sortby order
        if not sortby:
            sortby = 'state'
        sort_order = searchbar_sortings[sortby]['order']
        
        # count for pager
        expense_ids = expense_obj.sudo().search(domain)
        request_count = expense_ids.sudo().search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/expense",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=len(expense_ids),
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        requests = expense_obj.sudo().search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_expense_history'] = expense_ids.ids[:100]
        values.update({
            'date': date_begin,
            'expense_ids': expense_ids.sudo(),
            'page_name': 'expense',
            'pager': pager,
            'default_url': '/my/expense',
            'searchbar_sortings': searchbar_sortings,
            'create_expense' : True,
            'expence_category_ids' : self._get_expence_category(),
            'currency_ids' : self._get_expence_currency(),
            'sortby': sortby,
        })
        return request.render("hr_expense_portal.portal_my_expense", values)