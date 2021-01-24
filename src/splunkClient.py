import requests
import json

from enum import Enum

from exceptions import SplunkUpdateFailed, SplunkGetFailed
from exceptions import SplunkConnectFailed, SplunkValidateFailed
from exceptions import ConfigValidateFailed

requests.packages.urllib3.disable_warnings()

SEARCH_API = '/servicesNS/admin/{app}/saved/searches'


class SplunkClient(object):
    class Severity(Enum):
        DEBUG = 1
        INFO = 2
        WARN = 3
        ERROR = 4
        SEVERE = 5
        FATAL = 6
        Info = 1
        Low = 2
        Medium = 3
        High = 4
        Critical = 5

    class Priority(Enum):
        Highest = 1
        High = 2
        Normal = 3
        Low = 4
        Lowest = 5

    def __init__(self, host, port, username, password, verify=True):
        self._host = host
        self._port = port
        self._creds = (username, password)
        self._baseUrl = 'https://{}:{}'.format(host, port)
        self._verify = verify
        self._testConnection()

    def _testConnection(self):
        try:
            self.listSearches('search')
        except Exception as e:
            raise SplunkConnectFailed('Error: {} '.format(
                getattr(e, 'message', repr(e))
            ))

    def _searchExists(self, app, searchName):
        url = '{}{}/{}'.format(
            self._baseUrl,
            SEARCH_API.format(app=app),
            searchName
        )
        r = requests.get(url, auth=self._creds, verify=self._verify)

        return True if r.status_code == 200 else False

    def _mapActions(self, actionList):
        extra = {}

        for action in actionList:
            for name, config in action.items():

                if name == 'Add to Triggered Alerts':
                    extra['alert.track'] = 1

                if name == 'OpsGenie':
                    if extra.get('actions'):
                        extra['actions'] = extra['actions'] + ', opsgenie'
                    else:
                        extra['actions'] = 'opsgenie'
                    extra['action.opsgenie'] = 1

                if name == 'Send email' and config:
                    if extra.get('actions'):
                        extra['actions'] = extra['actions'] + ', email'
                    else:
                        extra['actions'] = 'email'

                    extra['action.email'] = 1
                    extra['action.email.to'] = config.get('To')

                    if config.get('Priority'):
                        extra['action.email.priority'] = getattr(
                            self.Priority,
                            config['Priority']
                        ).value
                    if config.get('Subject'):
                        extra['action.email.subject'] = config['Subject']

                    if config.get('Message'):
                        extra['action.email.message'] = config['Message']

                    if 'Link to Alert' in config['Include']:
                        extra['action.email.include.view_link'] = 1

                    if 'Link to Results' in config['Include']:
                        extra['action.email.include.results_link'] = 1

                    if 'Search String' in config['Include']:
                        extra['action.email.include.search'] = 1

                    if 'Inline Table' in config['Include']:
                        extra['action.email.inline'] = 1
                        extra['action.email.include.inline'] = 1
                        extra['action.email.include.format'] = 'table'

                    if 'Inline Raw' in config['Include']:
                        extra['action.email.inline'] = 1
                        extra['action.email.include.inline'] = 1
                        extra['action.email.include.format'] = 'raw'

                    if 'Inline CSV' in config['Include']:
                        extra['action.email.inline'] = 1
                        extra['action.email.include.inline'] = 1
                        extra['action.email.include.format'] = 'csv'

                    if 'Trigger Condition' in config['Include']:
                        extra['action.email.include.trigger'] = 1

                    if 'Trigger Time' in config['Include']:
                        extra['action.email.include.trigger_time'] = 1

                    if 'Attach CSV' in config['Include']:
                        extra['action.email.sendcsv'] = 1

                    if 'Attach PDF' in config['Include']:
                        extra['action.email.sendpdf'] = 1

                    if 'Allow Empty Attachment' in config['Include']:
                        extra['action.email.allow_empty_attachment'] = 1

                    if config.get('Type') and config.get('Type') == 'Plain':
                        extra['action.email.content_type'] = 'plain'
        if extra != {}:
            return extra
        else:
            raise ConfigValidateFailed(
                'No valid action specified! {}'.format(actionList)
            )

    def deploySearch(self, app, searchName, searchConfig):
        '''
        Updates a Splunk saved search, creating if it does not already exist.
        '''
        payload = {
            'search': searchConfig['search'],
            'description': searchConfig['description'],
            'cron_schedule': searchConfig['cron_schedule'],
            'is_scheduled': searchConfig['is_scheduled'],
            'alert.severity': getattr(
                self.Severity,
                searchConfig['severity']
            ).value,
            'dispatch.earliest_time': searchConfig['lookback'],
            'dispatch.latest_time': 'now'
        }
        payload.update(
            self._mapActions(searchConfig['actions'])
        )
        url = '{}{}'.format(self._baseUrl, SEARCH_API.format(app=app))

        if self._searchExists(app, searchName):
            url = '{}/{}'.format(url, searchName)
        else:
            payload['name'] = searchName

        url = url + '?output_mode=json'

        r = requests.post(
            url,
            auth=self._creds,
            data=payload,
            verify=self._verify
        )

        if r.status_code == 200 or r.status_code == 201:
            validated, error = self._validateSearch(app, searchName, payload)
            if not validated:
                raise SplunkValidateFailed(
                    'Search seemed to deploy, but validation failed! \n'
                    'Error message: {}\n'
                    'Check Splunk and fix as required.'.format(error)
                )
            return r.status_code

        else:
            details = json.loads(r.text)['messages'][0]
            raise SplunkUpdateFailed('{}: {}'.format(
                details['type'],
                details['text']
            ))

    def _compareActions(self, actionlist1, actionlist2):
        actions1 = actionlist1.split(',')
        actions2 = actionlist2.split(',')

        actions1 = [x.strip(' ') for x in actions1]
        actions2 = [x.strip(' ') for x in actions2]

        return sorted(actions1) == sorted(actions2)

    def _validateSearch(self, app, searchName, searchConfig):
        '''
        Validates a Splunk saved search exists matching the specified config.

        Returns: True if search on Splunk matches the expected config
                 False if not.
        '''

        url = '{}{}/{}?output_mode=json'.format(
            self._baseUrl,
            SEARCH_API.format(app=app),
            searchName
        )

        if not self._searchExists(app, searchName):
            return False, 'Search does not exist!'

        else:
            r = requests.get(url, auth=self._creds, verify=self._verify)

            if r.status_code != 200:
                details = json.loads(r.text)['messages'][0]
                raise SplunkGetFailed('{}: {}'.format(
                    details['type'],
                    details['text']
                ))

            response = json.loads(r.text)

            for search in response['entry']:
                # Search name does not match. Shouldn't ever be
                # possible as we've fetched the current config
                # using this name, but let's be paranoid and check!
                if search['name'] != searchName:
                    return False, 'Search name does not match!'

                searchConfig.pop('name', None)

                # Check each value in our config and ensure it matches
                # what is configured in Splunk.
                for key, value in searchConfig.items():
                    if not (
                        (
                            str(search['content'][key]) == str(value)
                        ) or (
                            search['content'][key] == value
                        )
                    ):
                        if (
                            ( key != 'actions') or (
                                key == 'actions' and not self._compareActions(
                                    searchConfig['actions'],
                                    search['content']['actions']
                                )
                            )
                        ):
                            error = (
                                "Validation of search '{}' in app '{}' "
                                'failed! Field {} has unexpected value {} '
                                '(expected {}).'.format(
                                    searchName,
                                    app,
                                    key,
                                    search['content'][key],
                                    value
                                ))
                            return False, error
                return True, ''

    def listSearches(self, app):
        '''
        List all searches in a given app
        '''
        url = '{}{}?output_mode=json'.format(
            self._baseUrl,
            SEARCH_API.format(app=app)
        )

        r = requests.get(url, auth=self._creds, verify=self._verify)

        if r.status_code != 200:
            details = json.loads(r.text)['messages'][0]
            raise SplunkGetFailed('{}: {}'.format(
                details['type'],
                details['text']
            ))

        response = json.loads(r.text)
        searchlist = []

        for search in response.get('entry'):
            searchlist.append(search['name'])
        return searchlist

    def deleteSearch(self, app, searchName):
        '''
        Delete a search in a given app
        '''
        url = '{}{}/{}'.format(
            self._baseUrl,
            SEARCH_API.format(app=app),
            searchName
        )

        r = requests.delete(url, auth=self._creds, verify=self._verify)

        if r.status_code != 200:
            details = json.loads(r.text)['messages'][0]
            raise SplunkUpdateFailed(
                'Failed to delete search {} in app {}! {}: {}'.format(
                    searchName,
                    app,
                    details['type'],
                    details['text']
                )
            )
