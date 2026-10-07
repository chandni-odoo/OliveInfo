import ast
import datetime

from dateutil import relativedelta
from collections import defaultdict
from odoo import api, Command, fields, models, _
from odoo.addons.helpdesk.models.helpdesk_ticket import TICKET_PRIORITY
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.web.controllers.main import clean_action
from odoo.osv import expression


class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"

    @api.model
    def retrieve_dashboard(self):
        domain = ['|', ('user_id', '=', self.env.uid), ('create_uid', '=', self.env.uid)]
        group_fields = ['priority', 'create_date', 'stage_id', 'close_hours']
        list_fields = ['priority', 'create_date', 'stage_id', 'close_hours']
        # TODO: remove SLA calculations if user_uses_sla is false.
        user_uses_sla = self.user_has_groups('helpdesk.group_use_sla') and \
                        bool(self.env['helpdesk.team'].search([('use_sla', '=', True)], limit=1))

        if user_uses_sla:
            group_fields.insert(1, 'sla_deadline:year')
            group_fields.insert(2, 'sla_deadline:hour')
            group_fields.insert(3, 'sla_reached_late')
            list_fields.insert(1, 'sla_deadline')
            list_fields.insert(2, 'sla_reached_late')

        HelpdeskTicket = self.env['helpdesk.ticket']
        tickets = HelpdeskTicket.search_read(expression.AND([domain, [('stage_id.is_close', '=', False)]]),
                                             ['sla_deadline', 'open_hours', 'sla_reached_late', 'priority'])

        result = {
            'helpdesk_target_closed': self.env.user.helpdesk_target_closed,
            'helpdesk_target_rating': self.env.user.helpdesk_target_rating,
            'helpdesk_target_success': self.env.user.helpdesk_target_success,
            'today': {'count': 0, 'rating': 0, 'success': 0},
            '7days': {'count': 0, 'rating': 0, 'success': 0},
            'my_all': {'count': 0, 'hours': 0, 'failed': 0},
            'my_high': {'count': 0, 'hours': 0, 'failed': 0},
            'my_urgent': {'count': 0, 'hours': 0, 'failed': 0},
            'show_demo': not bool(HelpdeskTicket.search([], limit=1)),
            'rating_enable': False,
            'success_rate_enable': user_uses_sla
        }

        def _is_sla_failed(data):
            deadline = data.get('sla_deadline')
            sla_deadline = fields.Datetime.now() > deadline if deadline else False
            return sla_deadline or data.get('sla_reached_late')

        def add_to(ticket, key="my_all"):
            result[key]['count'] += 1
            result[key]['hours'] += ticket['open_hours']
            if _is_sla_failed(ticket):
                result[key]['failed'] += 1

        for ticket in tickets:
            add_to(ticket, 'my_all')
            if ticket['priority'] == '2':
                add_to(ticket, 'my_high')
            if ticket['priority'] == '3':
                add_to(ticket, 'my_urgent')

        dt = fields.Date.context_today(self)
        tickets = HelpdeskTicket.read_group(domain + [('stage_id.is_close', '=', True), ('close_date', '>=', dt)],
                                            list_fields, group_fields, lazy=False)
        for ticket in tickets:
            result['today']['count'] += ticket['__count']
            if not _is_sla_failed(ticket):
                result['today']['success'] += ticket['__count']

        dt = fields.Datetime.to_string((datetime.date.today() - relativedelta.relativedelta(days=6)))
        tickets = HelpdeskTicket.read_group(domain + [('stage_id.is_close', '=', True), ('close_date', '>=', dt)],
                                            list_fields, group_fields, lazy=False)
        for ticket in tickets:
            result['7days']['count'] += ticket['__count']
            if not _is_sla_failed(ticket):
                result['7days']['success'] += ticket['__count']

        result['today']['success'] = fields.Float.round(
            result['today']['success'] * 100 / (result['today']['count'] or 1), 2)
        result['7days']['success'] = fields.Float.round(
            result['7days']['success'] * 100 / (result['7days']['count'] or 1), 2)
        result['my_all']['hours'] = fields.Float.round(result['my_all']['hours'] / (result['my_all']['count'] or 1), 2)
        result['my_high']['hours'] = fields.Float.round(result['my_high']['hours'] / (result['my_high']['count'] or 1),
                                                        2)
        result['my_urgent']['hours'] = fields.Float.round(
            result['my_urgent']['hours'] / (result['my_urgent']['count'] or 1), 2)

        if self.env['helpdesk.team'].search([('use_rating', '=', True)], limit=1):
            result['rating_enable'] = True
            # rating of today
            domain = [('user_id', '=', self.env.uid)]
            dt = fields.Date.today()
            tickets = self.env['helpdesk.ticket'].search(
                domain + [('stage_id.is_close', '=', True), ('close_date', '>=', dt)])
            activity = tickets.rating_get_grades()
            total_rating = self._compute_activity_avg(activity)
            total_activity_values = sum(activity.values())
            # In the 2 formula's below, we need to multiply at the end by (100 / MAX_SCORING)
            # where MAX_SCORING is defined in _compute_activity_avg as the value for a "great" rating.
            team_satisfaction = fields.Float.round(
                (total_rating / total_activity_values if total_activity_values else 0), 2) * 20
            if team_satisfaction:
                result['today']['rating'] = team_satisfaction

            # rating of last 7 days (6 days + today)
            dt = fields.Datetime.to_string((datetime.date.today() - relativedelta.relativedelta(days=6)))
            tickets = self.env['helpdesk.ticket'].search(
                domain + [('stage_id.is_close', '=', True), ('close_date', '>=', dt)])
            activity = tickets.rating_get_grades()
            total_rating = self._compute_activity_avg(activity)
            total_activity_values = sum(activity.values())
            team_satisfaction_7days = fields.Float.round(
                (total_rating / total_activity_values if total_activity_values else 0), 2) * 20
            if team_satisfaction_7days:
                result['7days']['rating'] = team_satisfaction_7days
        return result

