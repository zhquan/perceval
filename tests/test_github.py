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
import unittest

import httpretty
import requests

if not '..' in sys.path:
    sys.path.insert(0, '..')

from perceval.cache import Cache
from perceval.errors import BackendError, CacheError, ParseError
from perceval.backends.github import GitHub, GitHubCommand, GitHubClient


GITHUB_API_URL = "https://api.github.com"
GITHUB_ISSUES_URL = GITHUB_API_URL + "/repos/zhquan_example/repo/issues"
GITHUB_LOGIN_URL = GITHUB_API_URL + "/users/zhquan_example"
GITHUB_ORGS_URL = GITHUB_API_URL + "/users/zhquan_example/orgs"
GITHUB_COMMAND_URL = GITHUB_API_URL + "/command"


def read_file(filename, mode='r'):
    with open(filename, mode) as f:
        content = f.read()
    return content


class TestGitHubBackend(unittest.TestCase):
    """ GitHub backend tests """

    @httpretty.activate
    def test_fetch(self):
        """ Test whether a list of issues is returned """

        command = ""
        body = read_file('data/github_request')
        login = read_file('data/github_login')
        orgs = read_file('data/github_orgs')

        httpretty.register_uri(httpretty.GET,
                               GITHUB_COMMAND_URL,
                               body=command, status=200)
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL,
                               body=body,
                               status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986'
                               })
        httpretty.register_uri(httpretty.GET,
                              GITHUB_LOGIN_URL,
                              body=login, status=200)
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ORGS_URL,
                               body=orgs, status=200)

        github = GitHub("zhquan_example", "repo", "aaa", None)
        issues = [issues for issues in github.fetch()]
        json_body = json.loads(body)
        json_body[0]['user'] = json.loads(login)
        # Check requests
        expected = {
            "url": "https://api.github.com/repos/zhquan_example/repo/issues/1",
            "id": 1,
            "number": 1,
            "title": "Title 1",
            "__metadata__": {
                "backend_version": "0.1.0",
                "origin": "https://github.com/zhquan_example/repo",
                "backend_name": "GitHub",
                "updated_on": "2016-02-01T12:13:21Z"
            },
            "user": {
                "login": "zhquan_example",
                "id": 1,
                "url": "https://api.github.com/users/zhquan_example",
            },
            "comments": 4,
            "created_at": "2016-02-01T07:10:24Z",
            "updated_at": "2016-02-01T12:13:21Z",
            "closed_at": "2016-02-01T12:13:21Z",
            "pull_request": {
                "url": "https://api.github.com/repos/zhquan_example/repo/pulls/1",
                "html_url": "https://github.com/zhquan_example/repo/pull/1",
                "diff_url": "https://github.com/zhquan_example/repo/pull/1.diff",
                "patch_url": "https://github.com/zhquan_example/repo/pull/1.patch"
            },
            "body": "Body"
        }

        for key in expected:
            if (key == "__metadata__"):
                self.assertEqual(issues[0][key]["backend_version"], expected[key]["backend_version"])
                self.assertEqual(issues[0][key]["origin"], expected[key]["origin"])
                self.assertEqual(issues[0][key]["backend_name"], expected[key]["backend_name"])
                self.assertEqual(issues[0][key]["updated_on"], expected[key]["updated_on"])
            elif (key == "user"):
                self.assertEqual(issues[0][key]["login"], expected[key]["login"])
                self.assertEqual(issues[0][key]["url"], expected[key]["url"])
                self.assertEqual(issues[0][key]["id"], expected[key]["id"])
            else:
                self.assertEqual(issues[0][key], expected[key])

    @httpretty.activate
    def test_fetch_more_issues(self):
        """ Test when return two issues """

        command = ""
        login = read_file('data/github_login')
        issue_1 = read_file('data/github_issue_1')
        issue_2 = read_file('data/github_issue_2')

        httpretty.register_uri(httpretty.GET,
                               GITHUB_COMMAND_URL,
                               body=command, status=200)
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL,
                               body=issue_1,
                               status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986',
                                    'Link': '<'+GITHUB_ISSUES_URL+'/?&page=2>; rel="next", <'+GITHUB_ISSUES_URL+'/?&page=3>; rel="last"'
                               })
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL+'/?&page=2',
                               body=issue_2,
                               status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986'
                               })
        httpretty.register_uri(httpretty.GET,
                              GITHUB_LOGIN_URL,
                              body=login, status=200)
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ORGS_URL,
                               body="[]", status=200)

        github = GitHub("zhquan_example", "repo", "aaa", None)
        issues = [issues for issues in github.fetch()]

        # Check requests
        expected = {
            "assignee_data": {},
            "__metadata__": {
                "backend_version": "0.1.0",
                "origin": "https://github.com/zhquan_example/repo",
                "backend_name": "GitHub",
                "updated_on": "2016-03-15T15:09:29Z"
            },
            "milestone": None,
            "user_data": {
                "organizations_url": "https://api.github.com/users/zhquan_example/orgs",
                "updated_at": "2016-01-01T01:00:00Z",
                "id": 1,
                "organizations": [
                    {
                        'url': 'https://api.github.com/orgs/Orgs_1',
                        'login': 'Orgs_1',
                        'public_members_url': 'https://api.github.com/orgs/Orgs_1/public_members{/member}',
                        'hooks_url': 'https://api.github.com/orgs/Orgs_1/hooks',
                        'events_url': 'https://api.github.com/orgs/Orgs_1/events',
                        'issues_url': 'https://api.github.com/orgs/Orgs_1/issues',
                        'avatar_url': '',
                        'repos_url': 'https://api.github.com/orgs/Orgs_1/repos',
                        'id': 1,
                        'description': None,
                        'members_url': 'https://api.github.com/orgs/Orgs_1/members{/member}'
                    },
                    {
                        'url': 'https://api.github.com/orgs/Orgs_2',
                        'login': 'Orgs_2',
                        'public_members_url': 'https://api.github.com/orgs/Orgs_2/public_members{/member}',
                        'hooks_url': 'https://api.github.com/orgs/Orgs_2/hooks',
                        'events_url': 'https://api.github.com/orgs/Orgs_2/events',
                        'issues_url': 'https://api.github.com/orgs/Orgs_2/issues',
                        'avatar_url': '',
                        'repos_url': 'https://api.github.com/orgs/Orgs_2/repos',
                        'id': 2,
                        'description': None,
                        'members_url': 'https://api.github.com/orgs/Orgs_2/members{/member}'
                    }
                ],
                "login": "zhquan_example",
                "url": "https://api.github.com/users/zhquan_example"
            },
            "assignee": None
        }

        self.assertEqual(len(issues), 2)
        for key in expected:
            if (key == "__metadata__"):
                self.assertEqual(issues[1][key]["backend_version"], expected[key]["backend_version"])
                self.assertEqual(issues[1][key]["origin"], expected[key]["origin"])
                self.assertEqual(issues[1][key]["backend_name"], expected[key]["backend_name"])
                self.assertEqual(issues[1][key]["updated_on"], expected[key]["updated_on"])
            elif (key == "user_data"):
                self.assertEqual(issues[1][key]["organizations_url"], expected[key]["organizations_url"])
                self.assertEqual(issues[1][key]["updated_at"], expected[key]["updated_at"])
                self.assertEqual(issues[1][key]["id"], expected[key]["id"])
                self.assertEqual(issues[1][key]["organizations"], expected[key]["organizations"])
                self.assertEqual(issues[1][key]["login"], expected[key]["login"])
                self.assertEqual(issues[1][key]["url"], expected[key]["url"])
            else:
                self.assertEqual(issues[1][key], expected[key])

    @httpretty.activate
    def test_fetch_from_date(self):
        """ Test when return from date """

        requests = []
        command = ""
        login = read_file('data/github_login')
        body = read_file('data/github_issue_2')

        httpretty.register_uri(httpretty.GET,
                               GITHUB_COMMAND_URL,
                               body=command, status=200)
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL,
                               body=body,
                               status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986'
                               })
        httpretty.register_uri(httpretty.GET,
                              GITHUB_LOGIN_URL,
                              body=login, status=200)
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ORGS_URL,
                               body="[]", status=200)

        from_date = datetime.datetime(2016, 3, 1)
        github = GitHub("zhquan_example", "repo", "aaa", None)

        issues = [issues for issues in github.fetch(from_date=from_date)]

        # Check requests
        expected_issue = {
            "assignee_data": {},
            "__metadata__": {
                "backend_version": "0.1.0",
                "origin": "https://github.com/zhquan_example/repo",
                "backend_name": "GitHub",
                "updated_on": "2016-03-15T15:09:29Z"
            },
            "milestone": None,
            "user_data": {
                "organizations_url": "https://api.github.com/users/zhquan_example/orgs",
                "updated_at": "2016-01-01T01:00:00Z",
                "id": 1,
                "name": "zhquan_example",
                "organizations": [
                    {
                        'url': 'https://api.github.com/orgs/Orgs_1',
                        'login': 'Orgs_1',
                        'public_members_url': 'https://api.github.com/orgs/Orgs_1/public_members{/member}',
                        'hooks_url': 'https://api.github.com/orgs/Orgs_1/hooks',
                        'events_url': 'https://api.github.com/orgs/Orgs_1/events',
                        'issues_url': 'https://api.github.com/orgs/Orgs_1/issues',
                        'avatar_url': '',
                        'repos_url': 'https://api.github.com/orgs/Orgs_1/repos',
                        'id': 1,
                        'description': None,
                        'members_url': 'https://api.github.com/orgs/Orgs_1/members{/member}'
                    },
                    {
                        'url': 'https://api.github.com/orgs/Orgs_2',
                        'login': 'Orgs_2',
                        'public_members_url': 'https://api.github.com/orgs/Orgs_2/public_members{/member}',
                        'hooks_url': 'https://api.github.com/orgs/Orgs_2/hooks',
                        'events_url': 'https://api.github.com/orgs/Orgs_2/events',
                        'issues_url': 'https://api.github.com/orgs/Orgs_2/issues',
                        'avatar_url': '',
                        'repos_url': 'https://api.github.com/orgs/Orgs_2/repos',
                        'id': 2,
                        'description': None,
                        'members_url': 'https://api.github.com/orgs/Orgs_2/members{/member}'
                    }
                ],
                "login": "zhquan_example",
                "url": "https://api.github.com/users/zhquan_example"
            },
            "assignee": None
        }
        for key in expected_issue:
            if (key == "__metadata__"):
                self.assertEqual(issues[0][key]["backend_version"], expected_issue[key]["backend_version"])
                self.assertEqual(issues[0][key]["origin"], expected_issue[key]["origin"])
                self.assertEqual(issues[0][key]["backend_name"], expected_issue[key]["backend_name"])
                self.assertEqual(issues[0][key]["updated_on"], expected_issue[key]["updated_on"])
            elif (key == "user_data"):
                for u_key in expected_issue[key]:
                    self.assertEqual(expected_issue[key][u_key], issues[0][key][u_key])
            else:
                self.assertEqual(issues[0][key], expected_issue[key])

    @httpretty.activate
    def test_feth_empty(self):
        """ Test when return empty """

        command = ""
        body = ""
        login = read_file('data/github_login')

        httpretty.register_uri(httpretty.GET,
                               GITHUB_COMMAND_URL,
                               body=command, status=200)
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL,
                               body=body, status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986'
                               })
        httpretty.register_uri(httpretty.GET,
                              GITHUB_LOGIN_URL,
                              body=login, status=200)
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ORGS_URL,
                               body="[]", status=200)

        from_date = datetime.datetime(2016, 1, 1)
        github = GitHub("zhquan_example", "repo", "aaa", None)

        issues = [issues for issues in github.fetch(from_date=from_date)]

        self.assertEqual(len(issues), 0)


class TestGitHubBackendCache(unittest.TestCase):
    """GitHub backend tests using a cache"""

    def setUp(self):
        self.tmp_path = tempfile.mkdtemp(prefix='perceval_')

    def tearDown(self):
        shutil.rmtree(self.tmp_path)

    @httpretty.activate
    def test_fetch_from_cache(self):
        """ Test whether a list of issues is returned from cache """

        command = ""
        body = read_file('data/github_request')
        login = read_file('data/github_login')

        httpretty.register_uri(httpretty.GET,
                               GITHUB_COMMAND_URL,
                               body=command, status=200)
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL,
                               body=body, status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986'
                               })
        httpretty.register_uri(httpretty.GET,
                              GITHUB_LOGIN_URL,
                              body=login, status=200)
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ORGS_URL,
                               body="[]", status=200)

        # First, we fetch the bugs from the server, storing them
        # in a cache
        cache = Cache(self.tmp_path)
        github = GitHub("zhquan_example", "repo", "aaa", None, cache=cache)

        issues = [issues for issues in github.fetch()]

        # Now, we get the bugs from the cache.
        # The contents should be the same and there won't be
        # any new request to the server
        cache_issues = [cache_issues for cache_issues in github.fetch_from_cache()]

        for key in issues[0]:
            if (key == "__metadata__"):
                self.assertEqual(issues[0][key]["backend_version"], cache_issues[0][key]["backend_version"])
                self.assertEqual(issues[0][key]["origin"], cache_issues[0][key]["origin"])
                self.assertEqual(issues[0][key]["backend_name"], cache_issues[0][key]["backend_name"])
                self.assertEqual(issues[0][key]["updated_on"], cache_issues[0][key]["updated_on"])
            else:
                self.assertEqual(issues[0][key], cache_issues[0][key])

    def test_fetch_from_empty_cache(self):
        """Test if there are not any issues returned when the cache is empty"""

        cache = Cache(self.tmp_path)
        github = GitHub("zhquan_example", "repo", "aaa", None, cache=cache)

        cache_issues = [cache_issues for cache_issues in github.fetch_from_cache()]

        self.assertEqual(len(cache_issues), 0)

    def test_fetch_from_non_set_cache(self):
        """Test if a error is raised when the cache was not set"""

        github = GitHub("zhquan_example", "repo", "aaa", None)

        with self.assertRaises(CacheError):
            _ = [cache_issues for cache_issues in github.fetch_from_cache()]


class TestGitHubClient(unittest.TestCase):
    """ GitHub API client tests """

    @httpretty.activate
    def test_get_issues(self):
        """ Test get_issues API call """

        issue = read_file('data/github_request')

        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL,
                               body=issue, status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986'
                               })

        client = GitHubClient("zhquan_example", "repo", "aaa", None)
        raw_issues = [issues for issues in client.get_issues()]
        self.assertEqual(raw_issues[0], issue)

        # Check requests
        expected = {
                     'per_page': ['30'],
                     'state': ['all'],
                     'direction': ['asc'],
                     'sort': ['updated']
                   }

        self.assertDictEqual(httpretty.last_request().querystring, expected)
        self.assertEqual(httpretty.last_request().headers["Authorization"], "token aaa")

    @httpretty.activate
    def test_get_from_date_issues(self):
        """ Test get_from_issues API call """

        issue = read_file('data/github_request_from_2016_03_01')

        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL,
                               body=issue,
                               status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986'
                               })

        from_date = datetime.datetime(2016, 3, 1)
        client = GitHubClient("zhquan_example", "repo", "aaa", None)

        raw_issues = [issues for issues in client.get_issues(from_date)]
        self.assertEqual(raw_issues[0], issue)

        # Check requests
        expected = {
                     'per_page': ['30'],
                     'state': ['all'],
                     'direction': ['asc'],
                     'since': ['2016-03-01T00:00:00'],
                     'sort': ['updated']
                   }
        self.assertDictEqual(httpretty.last_request().querystring, expected)
        self.assertEqual(httpretty.last_request().headers["Authorization"], "token aaa")

    @httpretty.activate
    def test_get_page_issues(self):
        """ Test get_page_issue API call """

        issue_1 = read_file('data/github_issue_1')
        issue_2 = read_file('data/github_issue_2')

        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL,
                               body=issue_1,
                               status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986',
                                    'Link': '<'+GITHUB_ISSUES_URL+'/?&page=2>; rel="next", <'+GITHUB_ISSUES_URL+'/?&page=3>; rel="last"'
                               })
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL+'/?&page=2',
                               body=issue_2,
                               status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4985'
                               })

        client = GitHubClient("zhquan_example", "repo", "aaa", None)
        issues = [issues for issues in client.get_issues()]

        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0], issue_1)
        self.assertEqual(issues[1], issue_2)

        # Check requests
        expected = {
                     'per_page': ['30'],
                     'page': ['2'],
                     'state': ['all'],
                     'direction': ['asc'],
                     'sort': ['updated']
                   }

        self.assertDictEqual(httpretty.last_request().querystring, expected)
        self.assertEqual(httpretty.last_request().headers["Authorization"], "token aaa")

    @httpretty.activate
    def test_get_empty_issues(self):
        """ Test when issue is empty API call """

        issue = read_file('data/github_empty_request')

        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL,
                               body=issue, status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986'
                               })

        client = GitHubClient("zhquan_example", "repo", "aaa", None)

        raw_issues = [issues for issues in client.get_issues()]
        self.assertEqual(raw_issues[0], '[]\n')

        # Check requests
        expected = {
                     'per_page': ['30'],
                     'state': ['all'],
                     'direction': ['asc'],
                     'sort': ['updated']
                   }

        self.assertDictEqual(httpretty.last_request().querystring, expected)
        self.assertEqual(httpretty.last_request().headers["Authorization"], "token aaa")

    @httpretty.activate
    def test_get_user(self):
        """ Test get_user API call """

        login = read_file('data/github_login')

        httpretty.register_uri(httpretty.GET,
                               GITHUB_LOGIN_URL,
                               body=login, status=200)
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL,
                               body="",
                               status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986'
                               })

        client = GitHubClient("zhquan_example", "repo", "aaa", None)
        response = client.get_user("zhquan_example")
        self.assertEqual(response, login)

        _ = [issues for issues in client.get_issues()]

        # Check requests
        expected = {
                     'per_page': ['30'],
                     'state': ['all'],
                     'direction': ['asc'],
                     'sort': ['updated']
                   }

        self.assertDictEqual(httpretty.last_request().querystring, expected)
        self.assertEqual(httpretty.last_request().headers["Authorization"], "token aaa")

    @httpretty.activate
    def test_get_user_orgs(self):
        """ Test get_user_orgs API call """

        orgs = read_file('data/github_orgs')

        httpretty.register_uri(httpretty.GET,
                               GITHUB_ORGS_URL,
                               body=orgs, status=200)
        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL,
                               body="",
                               status=200,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986'
                               })

        client = GitHubClient("zhquan_example", "repo", "aaa", None)
        response = client.get_user_orgs("zhquan_example")

        self.assertEqual(response, orgs)

        _ = [issues for issues in client.get_issues()]

        # Check requests
        expected = {
                     'per_page': ['30'],
                     'state': ['all'],
                     'direction': ['asc'],
                     'sort': ['updated']
                   }

        self.assertDictEqual(httpretty.last_request().querystring, expected)
        self.assertEqual(httpretty.last_request().headers["Authorization"], "token aaa")

    @httpretty.activate
    def test_http_wrong_status(self):
        """Test if a error is raised when the http status was not 200"""

        issue = ""

        httpretty.register_uri(httpretty.GET,
                               GITHUB_ISSUES_URL,
                               body=issue,
                               status=500,
                               forcing_headers={
                                    'X-RateLimit-Remaining': '4986'
                               })

        client = GitHubClient("zhquan_example", "repo", "aaa", None)

        with self.assertRaises(requests.exceptions.HTTPError):
            _ = [issues for issues in client.get_issues()]

        # Check requests
        expected = {
                     'per_page': ['30'],
                     'state': ['all'],
                     'direction': ['asc'],
                     'sort': ['updated']
                   }

        self.assertDictEqual(httpretty.last_request().querystring, expected)
        self.assertEqual(httpretty.last_request().headers["Authorization"], "token aaa")

class TestGitHubCommand(unittest.TestCase):
    def test_parsing_on_init(self):
        """Test if the class is initialized"""

        args = ['--owner', 'zhquan_example',
                '--repository', 'repo',
                '--from-date', '2016-01-03',
                '-t', 'aaa']

        cmd = GitHubCommand(*args)
        self.assertIsInstance(cmd.parsed_args, argparse.Namespace)
        self.assertEqual(cmd.parsed_args.owner, "zhquan_example")
        self.assertEqual(cmd.parsed_args.repository, "repo")
        self.assertEqual(cmd.parsed_args.backend_token, "aaa")

    @httpretty.activate
    def test_argument_parser(self):
        """Test if it returns a argument parser object"""

        parser = GitHubCommand.create_argument_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)

if __name__ == "__main__":
    unittest.main(warnings='ignore')
