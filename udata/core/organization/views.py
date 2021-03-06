# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import request, g, jsonify, redirect, url_for
from flask.ext.security import current_user

from udata import search
from udata.app import nav
from udata.frontend import csv
from udata.frontend.views import DetailView, CreateView, EditView, SearchView, BaseView, SingleObject
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import db, Organization, Member, Reuse, Dataset, ORG_ROLES, User, Issue, FollowOrg
from udata.utils import get_by

from udata.core.dataset.csv import DatasetCsvAdapter, ResourcesCsvAdapter
from udata.core.activity.views import ActivityView

from .forms import OrganizationForm, OrganizationMemberForm, OrganizationExtraForm
from .permissions import EditOrganizationPermission, OrganizationPrivatePermission
from .tasks import notify_new_member


blueprint = I18nBlueprint('organizations', __name__, url_prefix='/organizations')


@blueprint.before_app_request
def set_g_user_orgs():
    if current_user.is_authenticated():
        g.user_organizations = current_user.organizations


navbar = nav.Bar('edit_org', [
    nav.Item(_('Descrition'), 'organizations.edit'),
    # nav.Item(_('Additional informations'), 'organizations.edit_extras'),
    nav.Item(_('Members'), 'organizations.edit_members'),
    nav.Item(_('Membership request'), 'organizations.edit_membership_requests'),
    nav.Item(_('Teams'), 'organizations.edit_teams'),
    nav.Item(_('Issues'), 'organizations.issues')
])


@blueprint.route('/', endpoint='list')
class OrganizationListView(SearchView):
    model = Organization
    context_name = 'organizations'
    template_name = 'organization/list.html'


class OrgView(object):
    model = Organization
    object_name = 'org'

    @property
    def organization(self):
        return self.get_object()

    def get_context(self):
        for item in navbar.items:
            item._args = {'org': self.organization}
        context = super(OrgView, self).get_context()
        context['can_edit'] = EditOrganizationPermission(self.organization)
        context['can_view'] = OrganizationPrivatePermission(self.organization)
        return context


class ProtectedOrgView(OrgView):
    def can(self, *args, **kwargs):
        permission = EditOrganizationPermission(self.organization)
        return permission.can()


@blueprint.route('/<org:org>/', endpoint='show')
class OrganizationDetailView(OrgView, DetailView):
    template_name = 'organization/display.html'
    nb_followers = 16
    page_size = 9

    def get_context(self):
        context = super(OrganizationDetailView, self).get_context()

        datasets = Dataset.objects(organization=self.organization).visible().order_by('-created')
        supplied_datasets = Dataset.objects(supplier=self.organization).visible().order_by('-created')
        reuses = Reuse.objects(organization=self.organization).visible().order_by('-created')
        followers = FollowOrg.objects.followers(self.organization).order_by('follower.fullname')

        can_edit = EditOrganizationPermission(self.organization)
        can_view = OrganizationPrivatePermission(self.organization)
        context.update({
            'reuses': reuses.paginate(1, self.page_size),
            'datasets': datasets.paginate(1, self.page_size),
            'supplied_datasets': supplied_datasets[:self.page_size],
            'followers': followers[:self.nb_followers],
            'can_edit': can_edit,
            'can_view': can_view,
            'private_reuses': list(Reuse.objects(organization=self.object).hidden()) if can_view else [],
            'private_datasets': list(Dataset.objects(organization=self.object).hidden()) if can_view else [],
        })

        return context


@blueprint.route('/<org:org>/dashboard/', endpoint='dashboard')
class OrganizationDashboardView(OrgView, ActivityView, DetailView):
    template_name = 'organization/dashboard.html'

    def get_context(self):
        context = super(OrganizationDashboardView, self).get_context()

        widgets = []

        if self.organization.metrics.get('datasets', 0) > 0:
            widgets.append({
                'title': _('Datasets'),
                'widgets': [
                    {
                        'title': _('Datasets'),
                        'metric': 'datasets',
                        'type': 'line',
                        'endpoint': 'datasets.list',
                        'args': {'org': self.organization}
                    },
                    {
                        'title': _('Views'),
                        'metric': 'dataset_views',
                        'data': 'datasets_nb_uniq_visitors',
                        'type': 'bar',
                        'endpoint': 'datasets.list',
                        'args': {'org': self.organization}
                    }
                ]
            })

        if self.organization.metrics.get('reuses') > 0:
            widgets.append({
                'title': _('Reuses'),
                'widgets': [
                    {
                        'title': _('Reuses'),
                        'metric': 'reuses',
                        'type': 'line',
                        'endpoint': 'reuses.list',
                        'args': {'org': self.organization}
                    },
                    {
                        'title': _('Views'),
                        'metric': 'reuse_views',
                        'data': 'reuses_nb_uniq_visitors',
                        'type': 'bar',
                        'endpoint': 'reuses.list',
                        'args': {'org': self.organization}
                    }
                ]
            })

        widgets.append({
            'title': _('Community'),
            'widgets': [
                {
                    'title': _('Permitted reuses'),
                    'metric': 'permitted_reuses',
                    'type': 'line',
                    # 'endpoint': 'reuses.list',
                    # 'args': {'org': self.organization}
                },
                {
                    'title': _('Followers'),
                    'metric': 'followers',
                    'type': 'line',
                }
            ]
        })

        context['metrics'] = widgets

        return context

    def filter_activities(self, qs):
        predicate = db.Q(organization=self.organization) | db.Q(related_to=self.organization)
        return qs(predicate)


@blueprint.route('/new/', endpoint='new')
class OrganizationCreateView(CreateView):
    model = Organization
    form = OrganizationForm
    template_name = 'organization/create.html'


@blueprint.route('/<org:org>/edit/', endpoint='edit')
class OrganizationEditView(ProtectedOrgView, EditView):
    form = OrganizationForm
    template_name = 'organization/edit.html'


@blueprint.route('/<org:org>/delete/', endpoint='delete')
class OrganizationDeleteView(ProtectedOrgView, SingleObject, BaseView):
    def post(self, org):
        org.deleted = datetime.now()
        org.save()
        return redirect(url_for('organizations.show', org=self.organization))


@blueprint.route('/<org:org>/edit/members/', endpoint='edit_members')
class OrganizationEditMembersView(ProtectedOrgView, EditView):
    form = OrganizationMemberForm
    template_name = 'organization/edit_members.html'

    def get_context(self):
        context = super(OrganizationEditMembersView, self).get_context()
        context['roles'] = ORG_ROLES
        return context

    def on_form_valid(self, form):
        user = User.objects.get_or_404(id=form.pk.data)
        member = get_by(self.organization.members, 'user', user)
        if member:
            member.role = form.value.data
        else:
            member = Member(user=user, role=form.value.data or 'editor')
            self.organization.members.append(member)
        self.organization.save()
        notify_new_member.delay(self.organization, member)
        return '', 200

    def on_form_error(self, form):
        return '', 400

    def delete(self, **kwargs):
        self.kwargs = kwargs
        user = User.objects.get_or_404(id=request.form.get('user_id'))
        member = get_by(self.organization.members, 'user', user)
        self.organization.members.remove(member)
        self.organization.save()
        return '', 204


@blueprint.route('/<org:org>/edit/requests/', endpoint='edit_membership_requests')
class OrganizationMembershipRequestsView(ProtectedOrgView, EditView):
    form = OrganizationForm
    template_name = 'organization/edit_membership_requests.html'


@blueprint.route('/<org:org>/edit/extras/', endpoint='edit_extras')
class OrganizationExtrasEditView(ProtectedOrgView, EditView):
    form = OrganizationExtraForm
    template_name = 'organization/edit_extras.html'

    def on_form_valid(self, form):
        if form.old_key.data:
            del self.organization.extras[form.old_key.data]
        self.organization.extras[form.key.data] = form.value.data
        self.organization.save()
        return jsonify({'key': form.key.data, 'value': form.value.data})


@blueprint.route('/<org:org>/edit/extras/<string:extra>/', endpoint='delete_extra')
class OrganizationExtraDeleteView(ProtectedOrgView, SingleObject, BaseView):
    def delete(self, org, extra, **kwargs):
        del org.extras[extra]
        org.save()
        return ''


@blueprint.route('/<org:org>/edit/teams/', endpoint='edit_teams')
class OrganizationEditTeamsView(ProtectedOrgView, EditView):
    form = OrganizationForm
    template_name = 'organization/edit_teams.html'


@blueprint.route('/<org:org>/issues/', endpoint='issues')
class OrganizationIssuesView(ProtectedOrgView, DetailView):
    template_name = 'organization/issues.html'

    def get_context(self):
        context = super(OrganizationIssuesView, self).get_context()
        datasets = Dataset.objects(organization=self.organization)
        reuses = Reuse.objects(organization=self.organization)
        ids = [o.id for o in list(datasets) + list(reuses)]
        context['issues'] = Issue.objects(subject__in=ids)
        return context


@blueprint.route('/<org:org>/datasets.csv')
def datasets_csv(org):
    datasets = search.iter(Dataset, organization=str(org.id))
    adapter = DatasetCsvAdapter(datasets)
    return csv.stream(adapter, '{0}-datasets'.format(org.slug))


@blueprint.route('/<org:org>/datasets-resources.csv')
def datasets_resources_csv(org):
    datasets = search.iter(Dataset, organization=str(org.id))
    adapter = ResourcesCsvAdapter(datasets)
    return csv.stream(adapter, '{0}-datasets-resources'.format(org.slug))


@blueprint.route('/<org:org>/supplied-datasets.csv')
def supplied_datasets_csv(org):
    datasets = search.iter(Dataset, supplier=str(org.id))
    adapter = DatasetCsvAdapter(datasets)
    return csv.stream(adapter, '{0}-supplied-datasets'.format(org.slug))


@blueprint.route('/<org:org>/supplied-datasets-resources.csv')
def supplied_datasets_resources_csv(org):
    datasets = search.iter(Dataset, supplier=str(org.id))
    adapter = ResourcesCsvAdapter(datasets)
    return csv.stream(adapter, '{0}-supplied-datasets-resources'.format(org.slug))
