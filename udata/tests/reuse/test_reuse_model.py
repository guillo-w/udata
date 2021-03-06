# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.models import Reuse

from .. import TestCase, DBTestMixin
from ..factories import ReuseFactory, UserFactory, OrganizationFactory


class ReuseModelTest(TestCase, DBTestMixin):
    def test_owned_by_user(self):
        user = UserFactory()
        reuse = ReuseFactory(owner=user)
        ReuseFactory(owner=UserFactory())

        result = Reuse.objects.owned_by(user)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], reuse)

    def test_owned_by_org(self):
        org = OrganizationFactory()
        reuse = ReuseFactory(organization=org)
        ReuseFactory(organization=OrganizationFactory())

        result = Reuse.objects.owned_by(org)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], reuse)

    def test_owned_by_org_or_user(self):
        user = UserFactory()
        org = OrganizationFactory()
        reuses = [ReuseFactory(owner=user), ReuseFactory(organization=org)]
        excluded = [ReuseFactory(owner=UserFactory()), ReuseFactory(organization=OrganizationFactory())]

        result = Reuse.objects.owned_by(org, user)

        self.assertEqual(len(result), 2)
        for reuse in result:
            self.assertIn(reuse, reuses)

        for reuse in excluded:
            self.assertNotIn(reuse, result)
