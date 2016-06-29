#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#     Quan Zhou <quan@bitergia.com>
#

import argparse
import datetime
import json
import shutil
import sys
import tempfile
import time
import unittest

import httpretty
import requests

if not '..' in sys.path:
    sys.path.insert(0, '..')

from perceval.cache import Cache
from perceval.errors import BackendError, CacheError, ParseError
from perceval.backends.stackexchange import StackExchange, StackExchangeCommand, StackExchangeClient


VERSION_API = '/2.2'
STACKEXCHANGE_API_URL = 'https://api.stackexchange.com'
STACKEXCHANGE_VERSION_URL = STACKEXCHANGE_API_URL + VERSION_API
STACKEXCHANGE_QUESTIONS_URL = STACKEXCHANGE_VERSION_URL + '/questions'
QUESTIONS_FILTER = 'Bf*y*ByQD_upZqozgU6lXL_62USGOoV3)MFNgiHqHpmO_Y-jHR'


def read_file(filename, mode='r'):
    with open(filename, mode) as f:
        content = f.read()
    return content


class TestStackExchangeBackend(unittest.TestCase):
    """StackExchange backend tests"""

    @httpretty.activate
    def test_fetch(self):
        """Test whether a list of questions is returned"""

        question = read_file('data/stackexchange/stackexchange_question')

        httpretty.register_uri(httpretty.GET,
                               STACKEXCHANGE_QUESTIONS_URL,
                               body=question, status=200)

        expected = {
            "origin": "stackoverflow",
            "perceval_version": "0.1.0",
            "backend_name": "StackExchange",
            "backend_version": "0.2.0"
        }

        stack = StackExchange(site="stackoverflow", tagged="python", token="aaa", max_questions=1)
        questions = [question for question in stack.fetch(from_date=None)]

        for key in expected:
            self.assertEqual(questions[0][key], expected[key])

        data = json.loads(question)
        self.assertDictEqual(questions[0]['data'], data['items'][0])

    @httpretty.activate
    def test_fetch_empty(self):
        """Test whether a list of questions is returned"""

        # Required fields
        question = '{"total": 0, "page_size": 0, "quota_remaining": 0, "quota_max": 0, "has_more": false, "items": []}'
        httpretty.register_uri(httpretty.GET,
                               STACKEXCHANGE_QUESTIONS_URL,
                               body=question, status=200)

        stack = StackExchange(site="stackoverflow", tagged="python", token="aaa", max_questions=1)
        questions = [question for question in stack.fetch(from_date=None)]

        self.assertEqual(len(questions), 0)

    @httpretty.activate
    def test_fetch_from_date(self):
        """Test whether a list of questions is returned"""

        question = read_file('data/stackexchange/stackexchange_question')

        httpretty.register_uri(httpretty.GET,
                               STACKEXCHANGE_QUESTIONS_URL,
                               body=question, status=200)

        expected = {
            "origin": "stackoverflow",
            "perceval_version": "0.1.0",
            "backend_name": "StackExchange",
            "backend_version": "0.2.0"
        }

        #unixtime = 1459900800
        from_date = datetime.datetime(2016, 4, 5)
        stack = StackExchange(site="stackoverflow", tagged="python", token="aaa", max_questions=1)
        questions = [question for question in stack.fetch(from_date=from_date)]

        #The date on the questions must be greater than from_date
        self.assertGreater(questions[0]['updated_on'], 1459900800)
        for key in expected:
            self.assertEqual(questions[0][key], expected[key])

        data = json.loads(question)
        self.assertDictEqual(questions[0]['data'], data['items'][0])

class TestStackExchangeBackendCache(unittest.TestCase):
    """StackExchange backend tests using a cache"""

    def setUp(self):
        self.tmp_path = tempfile.mkdtemp(prefix='perceval_')

    def tearDown(self):
        shutil.rmtree(self.tmp_path)

    @httpretty.activate
    def test_fetch_from_cache(self):
        """ Test whether a list of questions is returned from cache """

        question = read_file('data/stackexchange/stackexchange_question')

        httpretty.register_uri(httpretty.GET,
                               STACKEXCHANGE_QUESTIONS_URL,
                               body=question, status=200)

        # First, we fetch the bugs from the server, storing them
        # in a cache
        cache = Cache(self.tmp_path)
        stack = StackExchange(site="stackoverflow", tagged="python", token="aaa", max_questions=1, cache=cache)

        questions = [question for question in stack.fetch(from_date=None)]
        del questions[0]['timestamp']

        # Now, we get the bugs from the cache.
        # The contents should be the same and there won't be
        # any new request to the server
        cache_questions = [cache_question for cache_question in stack.fetch_from_cache()]
        del cache_questions[0]['timestamp']

        self.assertEqual(cache_questions, questions)

    def test_fetch_from_empty_cache(self):
        """Test if there are not any questions returned when the cache is empty"""

        cache = Cache(self.tmp_path)
        stack = StackExchange(site="stackoverflow", tagged="python", token="aaa", max_questions=1, cache=cache)

        cache_questions = [cache_question for cache_question in stack.fetch_from_cache()]

        self.assertEqual(len(cache_questions), 0)

    def test_fetch_from_non_set_cache(self):
        """Test if a error is raised when the cache was not set"""

        stack = StackExchange(site="stackoverflow", tagged="python", token="aaa", max_questions=1)

        with self.assertRaises(CacheError):
            _ = [cache_question for cache_question in stack.fetch_from_cache()]

class TestStackExchangeBackendParsers(unittest.TestCase):
    """StackExchange backend parsers tests"""

    def test_parse_questions(self):
        """Test question parsing"""

        raw_parse = read_file('data/stackexchange/stackexchange_question_page')
        parse = read_file('data/stackexchange/stackexchange_question_parse')
        parse = json.loads(parse)

        questions = StackExchange.parse_questions(raw_parse)

        result = [question for question in questions]

        self.assertDictEqual(result[0], parse[0])
        self.assertDictEqual(result[1], parse[1])

class TestStackExchangeClient(unittest.TestCase):
    """StackExchange API client tests"""

    @httpretty.activate
    def test_get_questions(self):
        """Test question API call"""

        question = read_file('data/stackexchange/stackexchange_question')

        httpretty.register_uri(httpretty.GET,
                               STACKEXCHANGE_QUESTIONS_URL,
                               body=question, status=200)

        payload = {
            'page': ['1'],
            'pagesize': ['1'],
            'order': ['desc'],
            'sort': ['activity'],
            'tagged': ['python'],
            'site': ['stackoverflow'],
            'key': ['aaa'],
            'filter': [QUESTIONS_FILTER]
        }

        client = StackExchangeClient(site="stackoverflow", tagged="python", token="aaa", max_questions=1)
        raw_questions = [questions for questions in client.get_questions(from_date=None)]

        self.assertEqual(len(raw_questions), 1)
        self.assertEqual(raw_questions[0], question)

        request = httpretty.last_request().querystring
        self.assertTrue(len(request), 1)
        self.assertDictEqual(request, payload)

    @httpretty.activate
    def test_get_question_empty(self):
        """ Test when question is empty API call """

        # Required fields
        question = '{"total": 0, "page_size": 0, "quota_remaining": 0, "quota_max": 0, "has_more": false}'

        httpretty.register_uri(httpretty.GET,
                               STACKEXCHANGE_QUESTIONS_URL,
                               body=question, status=200)

        payload = {
            'page': ['1'],
            'pagesize': ['1'],
            'order': ['desc'],
            'sort': ['activity'],
            'tagged': ['python'],
            'site': ['stackoverflow'],
            'key': ['aaa'],
            'filter': [QUESTIONS_FILTER]
        }

        client = StackExchangeClient(site="stackoverflow", tagged="python", token="aaa", max_questions=1)
        raw_questions = [questions for questions in client.get_questions(from_date=None)]

        self.assertEqual(len(raw_questions), 1)
        self.assertEqual(raw_questions[0], question)
        self.assertDictEqual(httpretty.last_request().querystring, payload)

    @httpretty.activate
    def test_get_questions_from_date(self):
        """Test question is returned from a given date"""

        question = read_file('data/stackexchange/stackexchange_question')

        httpretty.register_uri(httpretty.GET,
                               STACKEXCHANGE_QUESTIONS_URL,
                               body=question, status=200)

        from_date_unixtime = 1456876800 + time.timezone
        from_date = datetime.datetime(2016, 3, 2)

        payload = {
            'page': ['1'],
            'pagesize': ['1'],
            'order': ['desc'],
            'sort': ['activity'],
            'tagged': ['python'],
            'site': ['stackoverflow'],
            'key': ['aaa'],
            'filter': [QUESTIONS_FILTER],
            'min': [str(from_date_unixtime)]
        }

        client = StackExchangeClient(site="stackoverflow", tagged="python", token="aaa", max_questions=1)
        raw_questions = [questions for questions in client.get_questions(from_date=from_date)]

        self.assertEqual(len(raw_questions), 1)
        self.assertEqual(raw_questions[0], question)
        self.assertDictEqual(httpretty.last_request().querystring, payload)

    @httpretty.activate
    def test_get_questions_more(self):
        """Test question API call"""

        page_1 = read_file('data/stackexchange/stackexchange_question_page')
        page_2 = read_file('data/stackexchange/stackexchange_question_page_2')

        httpretty.register_uri(httpretty.GET,
                               STACKEXCHANGE_QUESTIONS_URL,
                               body=page_2,
                               status=200,
                               forcing_headers={
                                    'Link': '<'+STACKEXCHANGE_QUESTIONS_URL+'?&page=2>; rel="next", <'+STACKEXCHANGE_QUESTIONS_URL+'?&page=2>; rel="last"'
                               })
        httpretty.register_uri(httpretty.GET,
                               STACKEXCHANGE_QUESTIONS_URL+'?&page=2',
                               body=page_1,
                               status=200)
        payload = {
            'page': ['2'],
            'pagesize': ['1'],
            'order': ['desc'],
            'sort': ['activity'],
            'tagged': ['python'],
            'site': ['stackoverflow'],
            'key': ['aaa'],
            'filter': [QUESTIONS_FILTER]
        }

        client = StackExchangeClient(site="stackoverflow", tagged="python", token="aaa", max_questions=1)
        raw_questions = [questions for questions in client.get_questions(from_date=None)]

        self.assertEqual(len(raw_questions), 2)
        self.assertEqual(raw_questions[0], page_1)
        self.assertEqual(raw_questions[1], page_2)
        self.assertDictEqual(httpretty.last_request().querystring, payload)

class TestStackExchangeCommand(unittest.TestCase):

    @httpretty.activate
    def test_parsing_on_init(self):
        """Test if the class is initialized"""

        args = ['--site', 'stackoverflow',
                '--tagged', 'python',
                '--token', 'aaa',
                '--max-questions', "1"]

        cmd = StackExchangeCommand(*args)
        self.assertIsInstance(cmd.parsed_args, argparse.Namespace)
        self.assertEqual(cmd.parsed_args.site, "stackoverflow")
        self.assertEqual(cmd.parsed_args.tagged, "python")
        self.assertEqual(cmd.parsed_args.token, "aaa")
        self.assertEqual(cmd.parsed_args.max_questions, 1)

    def test_argument_parser(self):
        """Test if it returns a argument parser object"""

        parser = StackExchangeCommand.create_argument_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)

if __name__ == "__main__":
    unittest.main(warnings='ignore')
