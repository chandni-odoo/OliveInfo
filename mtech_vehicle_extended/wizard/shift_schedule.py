# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, date
import calendar
import pytz
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, Command
import json
from odoo.exceptions import UserError


class ShiftSchedule(models.Model):
    _name = "shift.schedule"
    _description = "Shift Schedule"
    _rec_name = 'task_id'

    collection_mode = fields.Selection([('fix', 'Fixed'), ('on_call', 'On Call')], string="Collection Mode")
    task_id = fields.Many2one('project.task', string="Task")
    vehicle_type = fields.Many2one('vehicle.type', string="Vehicle Type")
    permits_ids = fields.Many2many('vehicle.permit', 'vehicle_permit_rel', 'vehicle_id', 'permit_id', string="Permits")
    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('on_call', 'On Call'),
    ], string="Frequency")
    number_of_skips = fields.Integer(string="Number of Skips")
    minimum_trips_per_month = fields.Integer(string="Minimum Trips/Month")
    minimum_skips_per_do = fields.Integer(string="Minimum Skips per DO")

    start_date = fields.Date(
        string="Start Date",
        # default=lambda self: date(date.today().year, date.today().month, 1)
    )

    end_date = fields.Date(
        string="End Date",
        # default=lambda self: (date.today().replace(day=28) + timedelta(days=4) - timedelta(days=(date.today().replace(day=28) + timedelta(days=4)).day))
    )

    no_do_day = fields.Integer(string='No.DO/Day')
    no_do_week = fields.Integer(string='No.DO/Week')
    no_do_month = fields.Integer(string='No.DO/Month')
    plan_by = fields.Selection([
        ('date_wise', 'Date Wise'),
        ('day_wise', 'Day Wise')
    ], string='Plan By', default='date_wise')

    daily_advanced_details_ids = fields.One2many(
        'shift.schedule.advanced.details', 'schedule_id',
        string="Daily Advanced Details"
    )

    weekly_advanced_details_ids = fields.One2many(
        'shift.schedule.advanced.details', 'schedule_id',
        string="Weekly Advanced Details"
    )

    monthly_advanced_details_ids = fields.One2many(
        'shift.schedule.advanced.details', 'schedule_id',
        string="Monthly Advanced Details"
    )

    # manual_trip_first_month = fields.Integer(
    #     string='Manual Trip for First Month',
    #     help='Number of manual trips scheduled for the first month'
    # )

    remaining_days_first_month = fields.Integer(
        string='Remaining Days in First Month(Start Date)',
        # compute='_compute_manual_trip_and_remaining_days',
        compute='_compute_remaining_days',
        store=True,
        help='Number of remaining days in the month from start date'
    )

    last_schedule_data = fields.Text(string="Last Schedule Data", help="JSON serialized data of the last schedule")

    # @api.depends('start_date', 'frequency', 'plan_by')
    # def _compute_manual_trip_and_remaining_days(self):
    #     for record in self:
    #         if record.frequency == 'monthly' and record.plan_by in ['date_wise', 'day_wise']:
    #             record.manual_trip_first_month = 1
    #         else:
    #             record.manual_trip_first_month = 0

    #         if record.start_date:
    #             start_date = fields.Date.from_string(record.start_date)
    #             last_day = calendar.monthrange(start_date.year, start_date.month)[1]
    #             last_date = datetime(start_date.year, start_date.month, last_day).date()
    #             remaining_days = (last_date - start_date).days + 1

    #             if record.frequency == 'monthly' and record.plan_by in ['date_wise', 'day_wise']:
    #                 record.remaining_days_first_month = 1
    #             else:
    #                 record.remaining_days_first_month = remaining_days
    #         else:
    #             record.remaining_days_first_month = 0

    @api.depends('start_date', 'end_date')
    def _compute_remaining_days(self):
        for record in self:
            if record.start_date:
                start_date = fields.Date.from_string(record.start_date)
                last_day = calendar.monthrange(start_date.year, start_date.month)[1]
                last_date = datetime(start_date.year, start_date.month, last_day).date()
                remaining_days = (last_date - start_date).days + 1
                record.remaining_days_first_month = remaining_days
            else:
                record.remaining_days_first_month = 0

    def get_shift_dates(self, start_date, end_date, shift_day):
        """ Get all matching weekdays between start_date and end_date """
        from datetime import datetime, timedelta

        if not isinstance(shift_day, str):
            raise ValueError("shift_day must be a string, got %s instead" % type(shift_day))

        if isinstance(start_date, str):
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start = start_date

        if isinstance(end_date, str):
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end = end_date

        day_mapping = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2,
            'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
        }

        target_day = day_mapping.get(shift_day.lower())
        if target_day is None:
            raise ValueError("Invalid day provided: %s" % shift_day)

        shift_dates = []
        current = start

        while current <= end:
            if current.weekday() == target_day:
                shift_dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        return shift_dates
    
    def _prepare_schedule_data(self):
        """Prepare schedule data for serialization"""
        self.ensure_one()
        return {
            'start_date': self.start_date and self.start_date.strftime('%Y-%m-%d') or False,
            'end_date': self.end_date and self.end_date.strftime('%Y-%m-%d') or False,
            'collection_mode': self.collection_mode,
            'frequency': self.frequency,
            'vehicle_type': self.vehicle_type.id if self.vehicle_type else False,
            'permits_ids': self.permits_ids.ids,
            'number_of_skips': self.number_of_skips,
            'minimum_trips_per_month': self.minimum_trips_per_month,
            'minimum_skips_per_do': self.minimum_skips_per_do,
            'no_do_day': self.no_do_day,
            'no_do_week': self.no_do_week,
            'no_do_month': self.no_do_month,
            'plan_by': self.plan_by,
            'advanced_details': {
                'daily': [{
                    'shift_type': line.shift_type.id,
                    'day_name': line.day_name,
                    'vehicle_id': line.vehicle_id.id,
                    'no_trips': line.no_trips,
                    'start_time': line.start_time,
                    'interval_hours': line.interval_hours,
                } for line in self.daily_advanced_details_ids],
                'weekly': [{
                    'shift_type': line.shift_type.id,
                    'day_name': line.day_name,
                    'vehicle_id': line.vehicle_id.id,
                    'no_trips': line.no_trips,
                    'start_time': line.start_time,
                    'interval_hours': line.interval_hours,
                } for line in self.weekly_advanced_details_ids],
                'monthly': [{
                    'shift_type': line.shift_type.id,
                    'day_name': line.day_name,
                    'monthly_date': line.monthly_date,
                    'vehicle_id': line.vehicle_id.id,
                    'no_trips': line.no_trips,
                    'start_time': line.start_time,
                    'interval_hours': line.interval_hours,
                } for line in self.monthly_advanced_details_ids],
            }
        }
    
    
    def generate_schedule(self):
        for record in self:
            # First store the current configuration
            record.last_schedule_data = json.dumps(record._prepare_schedule_data())
            todo_stage = self.env["job.order.stage"].search([("name", "=", "To Do")], limit=1)
            in_progress_stage = self.env["job.order.stage"].search([("name", "=", "In Progress")], limit=1)

            if todo_stage and in_progress_stage:
                tasks = self.env["project.task"].search([("jobstage_id", "=", todo_stage.id)])
                tasks.write({"jobstage_id": in_progress_stage.id})

            for record in self:
                # DAILY SCHEDULING
                if record.frequency == 'daily':
                    if isinstance(record.start_date, str):
                        start_date = datetime.strptime(record.start_date, "%Y-%m-%d").date()
                    else:
                        start_date = record.start_date

                    if isinstance(record.end_date, str):
                        end_date = datetime.strptime(record.end_date, "%Y-%m-%d").date()
                    else:
                        end_date = record.end_date

                    current_date = start_date
                    while current_date <= end_date:
                        for line in record.daily_advanced_details_ids:
                            hours = int(line.start_time)
                            minutes = int(round((line.start_time - hours) * 60))
                            base_datetime = datetime.combine(current_date, datetime.min.time()).replace(hour=hours, minute=minutes)

                            if self.env.user.tz:
                                tz = pytz.timezone(self.env.user.tz)
                                base_datetime = tz.localize(base_datetime)
                            else:
                                base_datetime = pytz.utc.localize(base_datetime)

                            base_datetime_utc = base_datetime.astimezone(pytz.utc)
                            base_datetime_naive = base_datetime_utc.replace(tzinfo=None)

                            for trip_index in range(line.no_trips):
                                trip_datetime = base_datetime_naive + timedelta(hours=line.interval_hours * trip_index)

                                trip_rec = self.env['custom.trip.sheet'].create({
                                    'trip_type': 'trip',
                                    'customer_id': record.task_id.partner_id.id,
                                    # 'date_from': trip_datetime,
                                    # 'date_to': trip_datetime,
                                    'schedule_id': record.id,
                                    'vehicle_type_id': record.vehicle_type.id,
                                    'schedule_date': trip_datetime,
                                    'task_id': record.task_id.id,
                                    'shift_id': line.shift_type.id,
                                    'vehicle_no_id': line.vehicle_id.id,
                                    # 'skip_load_ids': [(0, 0, {
                                    #     'billable': True,
                                    #     'coll_del': 'collection',
                                    #     'qty': '',
                                    #     'unit_id': '',
                                    # })]
                                })

                                trip_rec.req_seq = trip_rec.sequence

                        current_date += timedelta(days=1)
                    record.task_id.schedule_id = record.id

                # WEEKLY SCHEDULING
                if record.frequency == 'weekly':
                    for line in record.weekly_advanced_details_ids:
                        shift_dates = self.get_shift_dates(record.start_date, record.end_date, line.day_name)
                        for shift_date in shift_dates:
                            hours = int(line.start_time)
                            minutes = int(round((line.start_time - hours) * 60))
                            base_datetime = datetime.strptime(shift_date, "%Y-%m-%d").replace(hour=hours, minute=minutes)

                            if self.env.user.tz:
                                tz = pytz.timezone(self.env.user.tz)
                                base_datetime = tz.localize(base_datetime)
                            else:
                                base_datetime = pytz.utc.localize(base_datetime)

                            base_datetime_utc = base_datetime.astimezone(pytz.utc)
                            base_datetime_naive = base_datetime_utc.replace(tzinfo=None)

                            for trip_index in range(line.no_trips):
                                trip_datetime = base_datetime_naive + timedelta(hours=line.interval_hours * trip_index)

                                trip_rec = self.env['custom.trip.sheet'].create({
                                    'trip_type': 'trip',
                                    'customer_id': record.task_id.partner_id.id,
                                    # 'date_from': trip_datetime,
                                    # 'date_to': trip_datetime,
                                    'schedule_id': record.id,
                                    'landfill_id': record.task_id.landfill_id.id,
                                    'vehicle_type_id': record.vehicle_type.id,
                                    'schedule_date': trip_datetime,
                                    'task_id': record.task_id.id,
                                    'shift_id': line.shift_type.id,
                                    'vehicle_no_id': line.vehicle_id.id,
                                    # 'skip_load_ids': [(0, 0, {
                                    #     'billable': True,
                                    #     'coll_del': 'collection',
                                    #     'qty': '',
                                    #     'unit_id': '',
                                    # })]
                                })
                                trip_rec.req_seq = trip_rec.sequence
                    record.task_id.schedule_id = record.id

                # MONTHLY SCHEDULING
                if record.frequency == 'monthly':
                    # --- PLAN BY: DATE_WISE ---
                    if record.plan_by == 'date_wise':
                        if isinstance(record.start_date, str):
                            start_date = datetime.strptime(record.start_date, "%Y-%m-%d").date()
                        else:
                            start_date = record.start_date

                        if isinstance(record.end_date, str):
                            end_date = datetime.strptime(record.end_date, "%Y-%m-%d").date()
                        else:
                            end_date = record.end_date

                        for line in record.monthly_advanced_details_ids:
                            try:
                                day_candidates = [int(val.strip()) for val in line.monthly_date.split(',')]
                            except (ValueError, AttributeError):
                                continue

                            dates_to_process = []
                            current_date = start_date
                            while current_date <= end_date:
                                year = current_date.year
                                month = current_date.month
                                last_day = calendar.monthrange(year, month)[1]
                                for candidate in day_candidates:
                                    if candidate <= last_day:
                                        new_date = date(year, month, candidate)
                                        if new_date >= start_date and new_date <= end_date:
                                            dates_to_process.append(new_date)
                                current_date += relativedelta(months=1)

                            for proc_date in dates_to_process:
                                hours = int(line.start_time)
                                minutes = int(round((line.start_time - hours) * 60))
                                base_datetime = datetime.combine(proc_date, datetime.min.time()).replace(hour=hours, minute=minutes)

                                if self.env.user.tz:
                                    tz = pytz.timezone(self.env.user.tz)
                                    base_datetime = tz.localize(base_datetime)
                                else:
                                    base_datetime = pytz.utc.localize(base_datetime)

                                base_datetime_utc = base_datetime.astimezone(pytz.utc)
                                base_datetime_naive = base_datetime_utc.replace(tzinfo=None)

                                for trip_index in range(line.no_trips):
                                    trip_datetime = base_datetime_naive + timedelta(hours=line.interval_hours * trip_index)
                                    trip_rec = self.env['custom.trip.sheet'].create({
                                        'trip_type': 'trip',
                                        'customer_id': record.task_id.partner_id.id,
                                        # 'date_from': trip_datetime,
                                        # 'date_to': trip_datetime,
                                        'schedule_id': record.id,
                                        'landfill_id': record.task_id.landfill_id.id,
                                        'vehicle_type_id': record.vehicle_type.id,
                                        'schedule_date': trip_datetime,
                                        'task_id': record.task_id.id,
                                        'shift_id': line.shift_type.id,
                                        'vehicle_no_id': line.vehicle_id.id,
                                        # 'skip_load_ids': [(0, 0, {
                                        #     'billable': True,
                                        #     'coll_del': 'collection',
                                        #     'qty': '',
                                        #     'unit_id': '',
                                        # })]
                                    })
                                    trip_rec.req_seq = trip_rec.sequence
                        record.task_id.schedule_id = record.id

                    # --- PLAN BY: DAY_WISE ---
                    elif record.plan_by == 'day_wise':
                        if isinstance(record.start_date, str):
                            start_date = datetime.strptime(record.start_date, "%Y-%m-%d").date()
                        else:
                            start_date = record.start_date

                        if isinstance(record.end_date, str):
                            end_date = datetime.strptime(record.end_date, "%Y-%m-%d").date()
                        else:
                            end_date = record.end_date

                        day_mapping = {
                            'monday': 0, 'tuesday': 1, 'wednesday': 2,
                            'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
                        }

                        for line in record.monthly_advanced_details_ids:
                            if not line.day_name:
                                continue
                            target_day = day_mapping.get(line.day_name.lower())
                            if target_day is None:
                                continue

                            current_date = start_date
                            while current_date <= end_date:
                                if current_date.weekday() == target_day:
                                    hours = int(line.start_time)
                                    minutes = int(round((line.start_time - hours) * 60))
                                    base_datetime = datetime.combine(current_date, datetime.min.time()).replace(hour=hours, minute=minutes)
                                    if self.env.user.tz:
                                        tz = pytz.timezone(self.env.user.tz)
                                        base_datetime = tz.localize(base_datetime)
                                    else:
                                        base_datetime = pytz.utc.localize(base_datetime)
                                    base_datetime_utc = base_datetime.astimezone(pytz.utc)
                                    base_datetime_naive = base_datetime_utc.replace(tzinfo=None)
                                    for trip_index in range(line.no_trips):
                                        trip_datetime = base_datetime_naive + timedelta(hours=line.interval_hours * trip_index)
                                        trip_rec = self.env['custom.trip.sheet'].create({
                                            'trip_type': 'trip',
                                            'customer_id': record.task_id.partner_id.id,
                                            # 'date_from': trip_datetime,
                                            # 'date_to': trip_datetime,
                                            'schedule_id': record.id,
                                            'landfill_id': record.task_id.landfill_id.id,
                                            'vehicle_type_id': record.vehicle_type.id,
                                            'schedule_date': trip_datetime,
                                            'task_id': record.task_id.id,
                                            'shift_id': line.shift_type.id,
                                            'vehicle_no_id': line.vehicle_id.id,
                                            # 'skip_load_ids': [(0, 0, {
                                            #     'billable': True,
                                            #     'coll_del': 'collection',
                                            #     'qty': '',
                                            #     'unit_id': '',
                                            # })]
                                        })
                                        trip_rec.req_seq = trip_rec.sequence
                                current_date += timedelta(days=1)
                        record.task_id.schedule_id = record.id
        return True
            

    @api.model
    def default_get(self, fields_list):
        res = super(ShiftSchedule, self).default_get(fields_list)
        
        # Get the context to check if we're coming from a task
        task_id = self._context.get('default_task_id') or res.get('task_id')
        
        if task_id:
            # Find the last schedule for this task
            last_schedule = self.search([('task_id', '=', task_id)], order='create_date desc', limit=1)
            
            if last_schedule and last_schedule.last_schedule_data:
                try:
                    data = json.loads(last_schedule.last_schedule_data)
                    
                    # Update basic fields
                    for field in data:
                        if field in fields_list and field != 'advanced_details':
                            res[field] = data[field]
                    
                    # Handle One2many fields using proper Command syntax
                    if 'advanced_details' in data:
                        res.update({
                            'daily_advanced_details_ids': [Command.create(line) for line in data['advanced_details'].get('daily', [])],
                            'weekly_advanced_details_ids': [Command.create(line) for line in data['advanced_details'].get('weekly', [])],
                            'monthly_advanced_details_ids': [Command.create(line) for line in data['advanced_details'].get('monthly', [])],
                        })
                    
                except Exception as e:
                    raise UserError(f"Error loading last schedule: {str(e)}")
        
        return res

    def action_load_last_schedule(self):
        """Load the last saved schedule configuration"""
        self.ensure_one()
        if not self.last_schedule_data:
            raise UserError("No previous schedule configuration found")
        
        try:
            data = json.loads(self.last_schedule_data)
        except json.JSONDecodeError:
            raise UserError("Invalid schedule data format")
        
        # Update basic fields
        vals = {
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'collection_mode': data.get('collection_mode'),
            'frequency': data.get('frequency'),
            'vehicle_type': data.get('vehicle_type'),
            'permits_ids': [(6, 0, data.get('permits_ids', []))],
            'number_of_skips': data.get('number_of_skips'),
            'minimum_trips_per_month': data.get('minimum_trips_per_month'),
            'minimum_skips_per_do': data.get('minimum_skips_per_do'),
            'no_do_day': data.get('no_do_day'),
            'no_do_week': data.get('no_do_week'),
            'no_do_month': data.get('no_do_month'),
            'plan_by': data.get('plan_by'),
        }
        
        self.write(vals)
        
        # Clear existing lines
        self.daily_advanced_details_ids.unlink()
        self.weekly_advanced_details_ids.unlink()
        self.monthly_advanced_details_ids.unlink()
        
        # Create new lines from saved data using proper Command syntax
        adv_details = data.get('advanced_details', {})
        
        if adv_details.get('daily'):
            self.daily_advanced_details_ids = [Command.create(line) for line in adv_details['daily']]
        
        if adv_details.get('weekly'):
            self.weekly_advanced_details_ids = [Command.create(line) for line in adv_details['weekly']]
        
        if adv_details.get('monthly'):
            self.monthly_advanced_details_ids = [Command.create(line) for line in adv_details['monthly']]
        
        return True
    

class ShiftScheduleAdvancedDetails(models.Model):
    _name = 'shift.schedule.advanced.details'
    _description = 'Advanced Details Weekly Planning'

    schedule_id = fields.Many2one('shift.schedule', string="Shift Schedule")
    shift_type = fields.Many2one('fleet.shift.type', "Shift Type")

    day_name = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string="Week Days")

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    no_trips = fields.Integer(string="No. Trips", default='1')
    start_time = fields.Float(string="Start Time")
    interval_hours = fields.Float(string="Interval (hours)")
    monthly_date = fields.Char(string='Monthly Date')
    vehicle_type = fields.Many2one('vehicle.type', string="Vehicle Type", related="schedule_id.vehicle_type", store=True)

    @api.onchange('vehicle_type')
    def _onchange_vehicle_type(self):
        """ Set domain for vehicle_id based on vehicle_type """
        if self.vehicle_type:
            return {
                'domain': {
                    'vehicle_id': [('active', '=', True), ('vehicle_type_id', '=', self.vehicle_type.id)]
                }
            }
        else:
            return {'domain': {'vehicle_id': [('active', '=', True)]}}
