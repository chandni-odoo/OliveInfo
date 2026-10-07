/** @odoo-module **/

import ActivityMenu from '@mail/js/systray/systray_activity_menu';
import session  from 'web.session';

ActivityMenu.include({
    //-----------------------------------------
    // Handlers
    //-----------------------------------------

    /**
     * @private
     * @override
     */
    _onActivityFilterClick: function (event) {
        // fetch the data from the button otherwise fetch the ones from the parent (.o_mail_preview).
        var data = _.extend({}, $(event.currentTarget).data(), $(event.target).data());
        var context = {};
        if (data.filter === 'my') {
            context['search_default_activities_overdue'] = 1;
            context['search_default_activities_today'] = 1;
        }
        else {
            context['search_default_activities_' + data.filter] = 1;
        }
        // Necessary because activity_ids of mail.activity.mixin has auto_join
        // So, duplicates are faking the count and "Load more" doesn't show up
        context['force_search_count'] = 1;

        var domain = [['activity_ids.user_id', '=', session.uid]]
        if (data.domain) {
            domain = domain.concat(data.domain)
        }
        if (data.approval_domain && data.filter === 'approval') {
            domain = domain.concat(data.approval_domain)
        }
        this.do_action({
            type: 'ir.actions.act_window',
            name: data.model_name,
            res_model:  data.res_model,
            views: this._getViewsList(data.res_model),
            search_view_id: [false],
            domain: domain,
            context:context,
        }, {
            clear_breadcrumbs: true,
        });
    },
});
