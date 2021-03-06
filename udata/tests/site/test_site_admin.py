# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.tests.frontend import FrontTestCase
from udata.tests.factories import AdminFactory


class SiteAdminTests(FrontTestCase):
    def test_render_config_form(self):
        '''It should render the site configuration form'''
        self.login(AdminFactory())
        response = self.get(url_for('admin.site'))
        self.assert200(response)

    def test_render_theme_config_form(self):
        '''It should render the site theme form'''
        self.login(AdminFactory())
        response = self.get(url_for('admin.theme'))
        self.assert200(response)
