# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import html5lib

from flask import render_template_string

from .. import TestCase, WebTestMixin

from udata.frontend.markdown import md, init_app, EXCERPT_TOKEN

parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder("dom"))


class MarkdownTestCase(TestCase, WebTestMixin):
    def create_app(self):
        app = super(MarkdownTestCase, self).create_app()
        init_app(app)
        return app

    def test_excerpt_is_not_removed(self):
        with self.app.test_request_context('/'):
            self.assertEqual(md(EXCERPT_TOKEN), EXCERPT_TOKEN)

    def test_markdown_filter_with_none(self):
        '''Markdown filter should not fails with None'''
        text = None
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)

        self.assertEqual(result, '')

    def test_markdown_links_nofollow(self):
        '''Markdown filter should render links as nofollow'''
        text = '[example](http://example.net/ "Title")'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            self.assertEqual(el.getAttribute('rel'), 'nofollow')
            self.assertEqual(el.getAttribute('href'), 'http://example.net/')
            self.assertEqual(el.getAttribute('title'), 'Title')
            self.assertEqual(el.firstChild.data, 'example')

    def test_markdown_linkify(self):
        '''Markdown filter should transform urls to anchors'''
        text = 'http://example.net/'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|markdown }}', text=text)
            parsed = parser.parse(result)
            el = parsed.getElementsByTagName('a')[0]
            self.assertEqual(el.getAttribute('rel'), 'nofollow')
            self.assertEqual(el.getAttribute('href'), 'http://example.net/')
            self.assertEqual(el.firstChild.data, 'http://example.net/')

    def test_mdstrip_filter(self):
        '''mdstrip should truncate the text before rendering'''
        text = '1 2 3 4 5 6 7 8 9 0'
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip(5) }}', text=text)

        self.assertEqual(result, '1 2 ...')

    def test_mdstrip_filter_does_not_truncate_without_size(self):
        '''mdstrip should not truncate by default'''
        text = 'aaaa ' * 300
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip }}', text=text)

        self.assertEqual(result.strip(), text.strip())

    def test_mdstrip_filter_with_none(self):
        '''mdstrip filter should not fails with None'''
        text = None
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip }}', text=text)

        self.assertEqual(result, '')

    def test_mdstrip_filter_with_excerpt(self):
        '''mdstrip should truncate on token if shorter than required size'''
        text = ''.join(['excerpt', EXCERPT_TOKEN, 'aaaa ' * 10])
        with self.app.test_request_context('/'):
            result = render_template_string('{{ text|mdstrip(20) }}', text=text)

        self.assertEqual(result, 'excerpt')
