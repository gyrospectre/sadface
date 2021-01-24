import sadface
import unittest
import os
import sys
import validator

from unittest.mock import MagicMock, patch

from nose2.tools import params


TEST_SEARCH = {
    'Test Search': {
        'description': 'Test search for validation',
        'search': 'index=*',
        'severity': 'High',
        'disabled': False,
        'lookback': '-1h',
        'cron_schedule': '* * * * *',
        'actions': [{'Add to Triggered Alerts': None}]
    }
}

GOOD_CONFIG = {
    'general': {
        'remove_unmanaged': ['splunk_enterprise_on_docker'],
        'warn_unmanaged': True
    },
    'splunk': {
        'host': 'localhost',
        'port': 8089,
        'verify': False,
        'secrets': {
            'order': ['env_vars'],
            'env_vars': {
                'username': 'SPLUNK_USER',
                'password': 'SPLUNK_PASS'
            }
        }
    }
}


class TestSadFace(unittest.TestCase):

    @patch.object(sadface, 'os')
    @patch.object(sadface, 'glob')
    @patch.object(sadface, 'benedict')
    def test_validate(self, mk_benedict, mk_glob, mk_os):
        mk_os.listdir = MagicMock(return_value=['testapp'])
        mk_glob.glob = MagicMock(return_value=['testfile'])
        mk_benedict.from_yaml = MagicMock(return_value=TEST_SEARCH)
        
        assert sadface.validate() == True

    @patch.object(sys, 'argv', ['sadface.py','deploy'])
    @patch.object(sadface, 'benedict')
    def test_loadConfigOK(self, mk_benedict):
        mk_benedict.from_yaml = MagicMock(return_value=GOOD_CONFIG) 
        assert sadface.main() == True
