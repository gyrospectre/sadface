import sadface
import unittest
import os
import sys
import validator

from unittest.mock import MagicMock, patch

from nose2.tools import params

from exceptions import ConfigLoadSecretsFailed

TEST_SEARCH = {
    'Test Search': {
        'description': 'Test search for validation',
        'search': 'index=*',
        'severity': 'High',
        'disabled': False,
        'lookback': '-1h',
        'cron_schedule': '* * * * *',
        'actions': [{'Add to Triggered Alerts': None}],
        'cyber': {
            'tactic': 'Impact',
            'technique': 'T1999'
        }
    }
}

GOOD_CONFIG_SM = {
    'general': {
        'remove_unmanaged': ['testapp'],
        'warn_unmanaged': True
    },
    'splunk': {
        'host': 'localhost',
        'port': 8089,
        'verify': False,
        'secrets': {
            'order': ['secrets_manager'],
            'secrets_manager': {
                'secret': 'dummy',
                'username': 'user',
                'password': 'pass'
            }
        }
    }
}

GOOD_CONFIG_ENV = {
    'general': {
        'remove_unmanaged': ['testapp'],
        'warn_unmanaged': True
    },
    'splunk': {
        'host': 'localhost',
        'port': 8089,
        'verify': False,
        'secrets': {
            'order': ['env_vars'],
            'env_vars': {
                'username': 'user',
                'password': 'pass'
            }
        }
    }
}

SECRETS_MGR_RESPONSE = {"user": "test", "pass": "pass123"}

class TestSadFace(unittest.TestCase):

    @patch.object(sadface, 'os')
    @patch.object(sadface, 'glob')
    @patch.object(sadface, 'benedict')
    def test_validate(self, mk_benedict, mk_glob, mk_os):
        mk_os.listdir = MagicMock(return_value=['testapp'])
        mk_glob.glob = MagicMock(return_value=['testfile'])
        mk_benedict.from_yaml = MagicMock(return_value=TEST_SEARCH)
        
        assert sadface.validate() == True

    @patch.object(sadface, 'validator')
    @patch.object(sadface, 'boto3')
    @patch.object(sadface, 'json')
    @patch.object(sadface, 'benedict')
    def test_loadConfigOK(self, mk_benedict, mk_json, mk_boto, mk_valid):
        mk_benedict.from_yaml = MagicMock(return_value=GOOD_CONFIG_SM)
        mk_json.loads = MagicMock(return_value=SECRETS_MGR_RESPONSE)
        mk_valid.validateConfig = MagicMock()

        assert sadface.loadConfig() == GOOD_CONFIG_SM

    @patch.object(sadface, 'os')
    @patch.object(sadface, 'validator')
    @patch.object(sadface, 'benedict')
    def test_loadConfigOKEnv(self, mk_benedict, mk_valid, mk_os):
        mk_benedict.from_yaml = MagicMock(return_value=GOOD_CONFIG_ENV)
        mk_valid.validateConfig = MagicMock()

        assert sadface.loadConfig() == GOOD_CONFIG_ENV

    @patch.object(sadface, 'os')
    @patch.object(sadface, 'validator')
    @patch.object(sadface, 'benedict')
    def test_loadConfigFailedEnv(self, mk_benedict, mk_valid, mk_os):
        mk_benedict.from_yaml = MagicMock(return_value=GOOD_CONFIG_ENV)
        mk_valid.validateConfig = MagicMock()
        mk_os.getenv.side_effect = Exception()

        with self.assertRaises(ConfigLoadSecretsFailed):
            sadface.loadConfig()

    @patch.object(sadface, 'validator')
    @patch.object(sadface, 'boto3')
    @patch.object(sadface, 'json')
    @patch.object(sadface, 'benedict')
    def test_loadConfigSMfail(self, mk_benedict, mk_json, mk_boto, mk_valid):
        mk_benedict.from_yaml = MagicMock(return_value=GOOD_CONFIG_SM)
        mk_json.loads = MagicMock(return_value=SECRETS_MGR_RESPONSE)
        mk_boto.client.side_effect = Exception
        mk_valid.validateConfig = MagicMock()

        with self.assertRaises(ConfigLoadSecretsFailed):
            sadface.loadConfig()

    @patch.object(sadface, 'os')
    @patch.object(sadface, 'glob')
    @patch.object(sadface, 'benedict')
    @patch.object(sadface, 'SplunkClient')
    @patch.object(sadface, 'loadConfig')
    def test_deployOK(self, mk_ldcfg, mk_splunk, mk_benedict, mk_glob, mk_os):
        mk_os.listdir = MagicMock(return_value=['testapp'])
        mk_glob.glob = MagicMock(return_value=['testfile'])
        mk_benedict.from_yaml = MagicMock(return_value=TEST_SEARCH)

        assert sadface.deploy() == None

    @patch.object(sadface, 'os')
    @patch.object(sadface, 'glob')
    @patch.object(sadface, 'benedict')
    @patch.object(sadface.SplunkClient, '__init__')
    @patch.object(sadface.SplunkClient, 'listSearches')
    @patch.object(sadface.SplunkClient, 'deploySearch')
    @patch.object(sadface, 'loadConfig')
    def test_deployExisting(self, mk_ldcfg, mk_ds, mk_list, mk_splunk, mk_benedict, mk_glob, mk_os):
        mk_ldcfg.return_value = GOOD_CONFIG_SM
        mk_splunk.return_value = None
        mk_list.return_value = ['Something else', 'Test Search']
        mk_os.listdir = MagicMock(return_value=['testapp'])
        mk_glob.glob = MagicMock(return_value=['testfile'])
        mk_benedict.from_yaml = MagicMock(return_value=TEST_SEARCH)
        mk_ds.return_value = 200

        assert sadface.deploy() == None

    @patch.object(sadface, 'deploy')
    @patch.object(sadface, 'loadConfig')
    def test_lambdaHandlerOKDebug(self, mk_ldcfg, mk_deploy):
        result = sadface.lambda_handler({'debug': True}, {})
    
        assert result['statusCode'] == 200

    @patch.object(sadface, 'deploy')
    @patch.object(sadface, 'loadConfig')
    def test_lambdaHandlerOK(self, mk_ldcfg, mk_deploy):
        result = sadface.lambda_handler({}, {})
    
        assert result['statusCode'] == 200

    def test_lambdaHandlerFail(self):
        result = sadface.lambda_handler({'debug': True}, {})
        assert result['statusCode'] == 500

    @patch.object(sadface, 'os')
    @patch.object(sadface, 'glob')
    @patch.object(sadface, 'benedict')
    @patch.object(sadface, 'SplunkClient')
    @patch.object(sadface, 'loadConfig')
    @patch.object(sys, 'argv', ['sadface.py','deploy', '--debug'])
    def test_deployCLI(self, mk_ldcfg, mk_splunk, mk_benedict, mk_glob, mk_os):
        assert sadface.main() == None
