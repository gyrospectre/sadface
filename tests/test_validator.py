import validator
import unittest

from unittest.mock import MagicMock, patch

from exceptions import ConfigValidateFailed

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

BAD_SEARCH = {
    'Test Search': {
        'description': 'Test search for validation',
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

BAD_CONFIG = {
    'general': {
        'remove_unmanaged': ['splunk_enterprise_on_docker'],
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

class TestValidator(unittest.TestCase):
    def setUp(self):
        self.validator = validator
        self.Validator = self.validator.Validator

    def test_validateSearchSuccess(self):
        result = self.validator.getValidSearch(TEST_SEARCH)
        assert result == TEST_SEARCH

    def test_validateSearchFailed(self):
        with self.assertRaises(
            (ConfigValidateFailed)
        ):
            self.validator.getValidSearch(BAD_SEARCH)

    def test_validateConfigSuccess(self):
        result = self.validator.validateConfig(GOOD_CONFIG,'src/schemas/sad-config.json')
        assert result == None

    def test_validateConfigFailed(self):
        with self.assertRaises(
            (ConfigValidateFailed)
        ):
            self.validator.validateConfig(BAD_CONFIG,'src/schemas/sad-config.json')
