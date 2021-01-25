import unittest
import json
import splunkClient
from requests import Response

from splunkClient import SplunkClient

from exceptions import ConfigValidateFailed, SplunkConnectFailed
from exceptions import SplunkGetFailed, SplunkValidateFailed, SplunkUpdateFailed

from unittest.mock import MagicMock, patch

from nose2.tools import params


VALID_SCONFIG = {
    'search': 'index=*',
    'description': 'Test',
    'cron_schedule': '* * * * *',
    'is_scheduled': 1,
    'severity': 'High',
    'lookback': '24h',
    'actions': [{'Add to Triggered Alerts': None}]
}

BAD_SCONFIG = {
    'search': 'index=*',
    'description': 'Something else',
    'cron_schedule': '* * * * *',
    'is_scheduled': 1,
    'severity': 'High',
    'lookback': '24h',
    'actions': [{'Add to Triggered Alerts': None}]
}

class TestInitClient(unittest.TestCase):

    @patch.object(splunkClient.SplunkClient, 'listSearches')
    def test_initClient(self, mk_list):
        client = SplunkClient(
            host="splunk.internal",
            port=8089,
            username="michael.j.fox",
            password="TeenWolf2021"
        )
        assert type(client) == SplunkClient

    @patch.object(splunkClient.SplunkClient, 'listSearches')
    def test_testConnSucceed(self, mk_list):
        assert SplunkClient._testConnection(SplunkClient) == None

    @patch.object(splunkClient.SplunkClient, '__init__')
    @patch.object(splunkClient.SplunkClient, 'listSearches')
    def test_testConnFail(self, mk_list, mk_init):
        mk_init.return_value = None
        mk_list.side_effect = SplunkGetFailed
        client = SplunkClient()

        with self.assertRaises(SplunkConnectFailed):
            client._testConnection()

class TestMapActions(unittest.TestCase):

    @params(
        [{'Add to Triggered Alerts': None}],
        [{'OpsGenie': None}],
        [
            {
                'Send email': {
                    'To': 'test@test.com',
                    'Include': []
                }
            }
        ]
    )
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_mapActionsSucceed(self, actionList, mk_init):
        mk_init.return_value = None

        client = splunkClient.SplunkClient()
        result = client._mapActions(actionList)

        assert type(result) == dict and result != {}

    @params(
        [
            {
                'Send email': {
                    'To': 'test@test.com',
                    'Include': [
                        'Link to Alert', 'Link to Results', 'Search String', 
                        'Inline Table', 'Inline Raw', 'Inline CSV', 'Trigger Condition',
                        'Trigger Time', 'Attach CSV', 'Attach PDF', 'Allow Empty Attachment'
                    ],
                    'Priority': 'Normal',
                    'Subject': 'Test',
                    'Message': 'msg',
                    'Type': 'Plain'
                }
            }
        ]
    )
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_mapActionsEmailSucceed(self, actionList, mk_init):
        mk_init.return_value=None

        client = SplunkClient()
        result = client._mapActions(actionList)

        assert result == {
            'actions': 'email',
            'action.email': 1,
            'action.email.to':
            'test@test.com',
            'action.email.priority': 3,
            'action.email.subject': 'Test',
            'action.email.message': 'msg',
            'action.email.include.view_link': 1,
            'action.email.include.results_link': 1, 
            'action.email.include.search': 1,
            'action.email.inline': 1,
            'action.email.include.inline': 1,
            'action.email.include.format': 'csv',
            'action.email.include.trigger': 1,
            'action.email.include.trigger_time': 1,
            'action.email.sendcsv': 1,
            'action.email.sendpdf': 1,
            'action.email.allow_empty_attachment': 1,
            'action.email.content_type': 'plain'
        }

    @params(
        [{'Bad Action': None}],
        [{'Send email': None}]
    )
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_mapActionsFail(self, actionList, mk_init):
        mk_init.return_value = None
        client = SplunkClient()

        with self.assertRaises(
            (ConfigValidateFailed)
        ):
            client._mapActions(actionList)

    @params(
        [
            {'OpsGenie': None},
            {'Send email': {'To': 'test@test.com','Include': []}}
        ],
        [
            {'Send email': {'To': 'test@test.com','Include': []}},
            {'OpsGenie': None}
        ]
    )
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_mapMultipleActions(self, actionList, mk_init):
        mk_init.return_value = None
        client = SplunkClient()
        result = client._mapActions(actionList)

        actions = result['actions']
        act = actions.split(',')
        act = [x.strip(' ') for x in act]
        act = sorted(act)

        assert act == ['email', 'opsgenie']

    def test_compareActions(self):
        result = SplunkClient._compareActions(SplunkClient, '1, 2', '2, 1')

        assert result == True

class TestSplunkAPI(unittest.TestCase):
    class SplunkResponse(Response):
        text = '''{
            "messages": [
                {
                    "type": "test",
                    "text": "This is a test."
                }
            ],
            "entry": [
                {
                    "name": "test",
                    "content": {
                        "search": "index=*",
                        "description": "Test",
                        "cron_schedule": "* * * * *",
                        "is_scheduled": 1,
                        "severity": "High",
                        "lookback": "24h",
                        "actions": "[{'Add to Triggered Alerts': 'None'}]"
                    } 
                }
            ]
        }'''
        status_code = 0

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_searchExists(self, mk_init, mk_req):
        mk_init.return_value = None

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False

        client._searchExists(searchName='test', app='test')

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_deployNewSearch(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 200
        splunkClient.requests.post.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False
        client._validateSearch = MagicMock(return_value=(True,''))
        client._searchExists = MagicMock(return_value=False)
        
        client.deploySearch(searchName='test', app='test', searchConfig=VALID_SCONFIG)

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_deployFailed(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 404
        splunkClient.requests.post.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False
        client._validateSearch = MagicMock(return_value=(True,'{}'))
        client._searchExists = MagicMock(return_value=False)
        
        with self.assertRaises(SplunkUpdateFailed):
            client.deploySearch(searchName='test', app='test', searchConfig=VALID_SCONFIG)

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_updateSearch(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 200
        splunkClient.requests.post.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False
        client._validateSearch = MagicMock(return_value=(True,''))
        client._searchExists = MagicMock(return_value=True)
        
        client.deploySearch(searchName='test', app='test', searchConfig=VALID_SCONFIG)

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_validateSuccess(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 200
        splunkClient.requests.get.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False
        client._searchExists = MagicMock(return_value=True)
        client._compareActions = MagicMock(return_value=True)
        result, error = client._validateSearch(searchName='test', app='test', searchConfig=VALID_SCONFIG)

        assert result == True
        assert error == ''

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_validateFailedNotExists(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 200
        splunkClient.requests.get.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False
        client._searchExists = MagicMock(return_value=False)

        result, error = client._validateSearch(searchName='test', app='test', searchConfig=VALID_SCONFIG)
        assert result == False
        assert error == 'Search does not exist!'

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_validateFailed404(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 404
        splunkClient.requests.get.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False
        client._searchExists = MagicMock(return_value=True)

        with self.assertRaises(
            (SplunkGetFailed)
        ):
            client._validateSearch(searchName='test', app='test', searchConfig=VALID_SCONFIG)

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_validateFailedDiffName(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 200
        splunkClient.requests.get.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False
        client._searchExists = MagicMock(return_value=True)
        client._compareActions = MagicMock(return_value=True)

        result,error = client._validateSearch(searchName='test2', app='test', searchConfig=VALID_SCONFIG)
        assert result == False
        assert error == 'Search name does not match!'

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_validateFailedDiffValue(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 200
        splunkClient.requests.get.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False
        client._searchExists = MagicMock(return_value=True)
    
        result,error = client._validateSearch(searchName='test', app='test', searchConfig=BAD_SCONFIG)
        assert result == False
        assert error == "Validation of search 'test' in app 'test' failed! Field description has unexpected value Test (expected Something else)."

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_validateFailedDeploy(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 200
        splunkClient.requests.post.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False
        client._validateSearch = MagicMock(return_value=(False,''))
        client._searchExists = MagicMock(return_value=False)

        with self.assertRaises(
            (SplunkValidateFailed)
        ):
            client.deploySearch(searchName='test', app='test', searchConfig=VALID_SCONFIG)

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_listSearchesSuccess(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 200
        splunkClient.requests.get.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False
        result = client.listSearches(app='test')
        assert result == ['test']

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_listSearchesFail(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 404
        splunkClient.requests.get.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False

        with self.assertRaises(
            (SplunkGetFailed)
        ):
            client.listSearches(app='test')

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_deleteSearchSuccess(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 200
        splunkClient.requests.delete.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False
        result = client.deleteSearch(app='test', searchName='test')
        assert result == None

    @patch.object(splunkClient, 'requests')
    @patch.object(splunkClient.SplunkClient, '__init__')
    def test_deleteSearchFail(self, mk_init, mk_req):
        mk_init.return_value = None
        r = self.SplunkResponse
        r.status_code = 404
        splunkClient.requests.delete.return_value = r

        client = SplunkClient()
        client._baseUrl = ''
        client._creds = ''
        client._verify = False
        with self.assertRaises(
            (SplunkUpdateFailed)
        ):
            client.deleteSearch(app='test', searchName='test')
