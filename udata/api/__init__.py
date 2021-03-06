# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import datetime
from functools import wraps

from flask import current_app, g, request, url_for, json, make_response, redirect, Blueprint
from flask.ext.restplus import Api, Resource, marshal
from flask.ext.restful.utils import cors

from udata import search, theme
from udata.app import csrf
from udata.i18n import I18nBlueprint
from udata.auth import current_user, login_user, Permission, RoleNeed, PermissionDenied
from udata.utils import multi_to_dict
from udata.core.user.models import User

from . import fields, oauth2

log = logging.getLogger(__name__)

apiv1 = Blueprint('api', __name__, url_prefix='/api/1')
apidoc = I18nBlueprint('apidoc', __name__)


DEFAULT_PAGE_SIZE = 50
HEADER_API_KEY = 'X-API-KEY'


class UDataApi(Api):
    def __init__(self, app=None, **kwargs):
        kwargs['decorators'] = [self.authentify] + (kwargs.pop('decorators', []) or [])
        super(UDataApi, self).__init__(app, **kwargs)
        self.authorizations = {'apikey': {'type': 'apiKey', 'passAs': 'header', 'keyname': HEADER_API_KEY}}

    def secure(self, func):
        '''Enforce authentication on a given method/verb and optionnaly check a given permission'''
        if isinstance(func, basestring):
            return self._apply_permission(Permission(RoleNeed(func)))
        elif isinstance(func, Permission):
            return self._apply_permission(func)
        else:
            return self._apply_secure(func)

    def _apply_permission(self, permission):
        def wrapper(func):
            return self._apply_secure(func, permission)
        return wrapper

    def _apply_secure(self, func, permission=None):
        '''Enforce authentication on a given method/verb'''
        self._handle_api_doc(func, {'authorizations': 'apikey'})

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated():
                self.abort(401)

            if permission is not None:
                with permission.require(403):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    def authentify(self, func):
        '''Authentify the user if credentials are given'''
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated():
                return func(*args, **kwargs)

            apikey = request.headers.get(HEADER_API_KEY)
            if apikey:
                try:
                    user = User.objects.get(apikey=apikey)
                except User.DoesNotExist:
                    self.abort(401, 'Invalid API Key')

                if not login_user(user, False):
                    self.abort(401, 'Inactive user')
            else:
                oauth2.check_credentials()
            return func(*args, **kwargs)
        return wrapper

    def validate(self, form_cls, obj=None):
        '''Validate a form from the request and handle errors'''
        form = form_cls.from_json(request.json, obj=obj, instance=obj, csrf_enabled=False)
        if not form.validate():
            self.abort(400, errors=form.errors)
        return form

    def render_ui(self):
        return redirect(url_for('apii18n.apidoc'))

    def search_parser(self, adapter, paginate=True):
        parser = self.parser()
        # q parameter
        parser.add_argument('q', type=str, location='args', help='The search query')
        # Add facets filters arguments
        for name, facet in adapter.facets.items():
            parser.add_argument(name, type=str, location='args')
        # Sort arguments
        choices = adapter.sorts.keys() + ['-' + k for k in adapter.sorts.keys()]
        parser.add_argument('sort', type=str, location='args', choices=choices)
        if paginate:
            parser.add_argument('page', type=int, location='args', default=0, help='The page to display')
            parser.add_argument('page_size', type=int, location='args', default=20, help='The page size')
        return parser

    def unauthorized(self, response):
        '''Override to change the WWW-Authenticate challenge'''
        realm = current_app.config.get('HTTP_OAUTH_REALM', 'uData')
        challenge = 'Bearer realm="{0}"'.format(realm)

        response.headers['WWW-Authenticate'] = challenge
        return response

    def page_parser(self):
        parser = self.parser()
        parser.add_argument('page', type=int, default=1, location='args', help='The page to fetch')
        parser.add_argument('page_size', type=int, default=20, location='args', help='The page size to fetch')
        return parser


api = UDataApi(apiv1, ui=False,
    decorators=[csrf.exempt, cors.crossdomain(origin='*', credentials=True)],
    version='1.0', title='uData API',
    description='uData API', default='site', default_label='Site global namespace'
)


@api.representation('application/json')
def output_json(data, code, headers=None):
    '''Use Flask JSON to serialize'''
    resp = make_response(json.dumps(data), code)
    resp.headers.extend(headers or {})
    return resp


@apiv1.before_request
def set_api_language():
    if 'lang' in request.args:
        g.lang_code = request.args['lang']


@api.errorhandler(PermissionDenied)
def handle_permission_denied(error):
    return {
        'message': str(error),
        'status': 403
    }, 403


@api.errorhandler(ValueError)
def handle_value_error(error):
    return {
        'message': str(error),
        'status': 400
    }, 400


@apidoc.route('/api/')
@apidoc.route('/api/1/')
def default_api():
    return redirect(url_for('apidoc.swaggerui'))


@apidoc.route('/apidoc/')
def swaggerui():
    return theme.render('apidoc.html', specs_url=api.specs_url)


@apidoc.route('/apidoc/images/<path:path>')
def images(path):
    return redirect(url_for('static', filename='bower/swagger-ui/dist/images/' + path))


@apidoc.route('/static/images/throbber.gif')
def fix_apidoc_throbber():
    return redirect(url_for('static', filename='bower/swagger-ui/dist/images/throbber.gif'))


class API(Resource):  # Avoid name collision as resource is a core model
    pass


class ModelListAPI(API):
    model = None
    fields = None
    form = None
    search_adapter = None

    @api.doc(params={})
    def get(self):
        '''List all objects'''
        if self.search_adapter:
            objects = search.query(self.search_adapter, **multi_to_dict(request.args))
        else:
            objects = list(self.model.objects)
        return marshal_page(objects, self.fields)

    @api.secure
    @api.doc(responses={400: 'Validation error'})
    def post(self):
        '''Create a new object'''
        form = api.validate(self.form)
        return marshal(form.save(), self.fields), 201


class SingleObjectAPI(object):
    model = None

    def get_or_404(self, **kwargs):
        for key, value in kwargs.items():
            if isinstance(value, self.model):
                return value
        return self.model.objects.get_or_404(**kwargs)


@api.doc(responses={404: 'Object not found'})
class ModelAPI(SingleObjectAPI, API):
    fields = None
    form = None

    def get(self, **kwargs):
        '''Get a given object'''
        obj = self.get_or_404(**kwargs)
        return marshal(obj, self.fields)

    @api.secure
    @api.doc(responses={400: 'Validation error'})
    def put(self, **kwargs):
        '''Update a given object'''
        obj = self.get_or_404(**kwargs)
        form = api.validate(self.form, obj)
        return marshal(form.save(), self.fields)

    @api.secure
    @api.doc(model=None, responses={204: 'Object deleted'})
    def delete(self, **kwargs):
        '''Delete a given object'''
        obj = self.get_or_404(**kwargs)
        if hasattr(obj, 'deleted'):
            obj.deleted = datetime.now()
            obj.save()
        else:
            obj.delete()
        return '', 204


base_reference = api.model('BaseReference', {
    'id': fields.String(description='The object unique identifier', required=True),
    'class': fields.ClassName(description='The object class', discriminator=True, required=True),
}, description='Base model for reference field, aka. inline model reference')



def marshal_page(page, page_fields):
    return api.marshal(page, fields.pager(page_fields))


def marshal_page_with(func):
    pass


def init_app(app):
    # Load all core APIs
    import udata.core.spatial.api
    import udata.core.metrics.api
    import udata.core.user.api
    import udata.core.dataset.api
    import udata.core.reuse.api
    import udata.core.organization.api
    import udata.core.followers.api
    import udata.core.jobs.api
    import udata.core.site.api
    import udata.core.tags.api
    import udata.core.topic.api
    import udata.core.post.api
    import udata.features.transfer.api

    # Load plugins API
    for plugin in app.config['PLUGINS']:
        name = 'udata.ext.{0}.api'.format(plugin)
        try:
            __import__(name)
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s: %s', name, e)

    # api.init_app(app)
    app.register_blueprint(apidoc)
    app.register_blueprint(apiv1)

    oauth2.init_app(app)
