import boto3
import cli
import glob
import json
import json_logging
import logging
import os
import sys
import validator

from exceptions import ConfigLoadSecretsFailed

from splunkClient import SplunkClient

from benedict import benedict


LOGGER = logging.getLogger("sad")
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler(sys.stdout))
VALID_COMMANDS = ['deploy', 'validate']
CONFIG_FILE = 'config.yaml'


def validate():
    for app in os.listdir('content'):
        for file in glob.glob('content/{}/searches/*.yaml'.format(app)):
            LOGGER.debug('Validating {}.'.format(file))
            sourcefile = benedict.from_yaml(file)
            validator.getValidSearch(sourcefile)
    print("Valid")
    return True

def loadConfig():

    # Account for difference in pwd for CLI and
    # lamdba invokation methods
    schema = 'schemas/sad-config.json'
    if sys._getframe(2).f_code.co_name == 'main':
        configFile = 'src/' + CONFIG_FILE
        schema = 'src/' + schema
    else:
        configFile = CONFIG_FILE

    cfg = benedict.from_yaml(configFile)

    validator.validateConfig(
        config=cfg,
        schemafile=schema
    )
    LOGGER.debug('Loaded and validated SAD config successfully.')

    for location in cfg['splunk']['secrets']['order']:
        secretConfig = cfg['splunk']['secrets'][location]
        if location == 'secrets_manager':
            try:
                client = boto3.client('secretsmanager')
                secretRaw = client.get_secret_value(
                    SecretId=secretConfig['secret']
                )
                secret = json.loads(secretRaw['SecretString'])

                cfg['splunk']['username'] = secret[secretConfig['username']]
                cfg['splunk']['password'] = secret[secretConfig['password']]

                if cfg['splunk']['username'] and cfg['splunk']['password']:
                    LOGGER.debug(
                        'Successfully loaded secrets from Secrets Manager.'
                    )
                    return cfg
            except Exception as e:
                LOGGER.debug('Could not fetch from SM: {}.'.format(e))
                continue

        elif location == 'env_vars':
            try:
                cfg['splunk']['username'] = os.getenv(secretConfig['username'])
                cfg['splunk']['password'] = os.getenv(secretConfig['password'])
                if cfg['splunk']['username'] and cfg['splunk']['password']:
                    LOGGER.debug('Successfully loaded secrets from env vars.')
                    return cfg
            except Exception as e:
                LOGGER.debug('Could not fetch from env vars: {}.'.format(e))
                continue

    raise ConfigLoadSecretsFailed('Could not find secrets!')


def deploy():
    config = loadConfig()

    splunkConfig = {
        k: config['splunk'][k] for k in config['splunk'] if k != 'secrets'
    }
    splunk = SplunkClient(
        **splunkConfig
    )

    LOGGER.info('Connected to Splunk instance.')
    LOGGER.info('Starting deploy.')

    for app in os.listdir('content'):
        LOGGER.info("Deploying saved search content for app '{}'".format(app))
        searchlist = splunk.listSearches(app=app)
        processed = 0
        for file in glob.glob('content/{}/searches/*.yaml'.format(app)):
            LOGGER.debug('Processing {}.'.format(file))
            sourcefile = benedict.from_yaml(file)
            searches = validator.getValidSearch(sourcefile)

            searchconfig = {}
            for searchname, details in searches.items():
                # We only support alerts, not reports
                searchconfig['is_scheduled'] = 'True'

                if 'cyber' in details:
                    details['cyber']['Detection'] = searchname
                    details['cyber']['Severity'] = details['severity']
                    for variable, value in details['cyber'].items():
                        details['search'] = '{} | eval {}="{}"'.format(
                            details['search'],
                            variable,
                            value
                        )
                    details.pop('cyber', None)

                searchconfig.update(details)
                result = splunk.deploySearch(app, searchname, searchconfig)
                if result == 200:
                    prefix = 'updated'
                else:
                    prefix = 'created'

                LOGGER.debug("Search '{}' in app '{}' {} successfully.".format(
                    searchname,
                    app,
                    prefix
                ))
                processed += 1

                if searchname in searchlist:
                    searchlist.remove(searchname)

        LOGGER.info('{} searches processed.'.format(
            processed
        ))

        if len(searchlist) > 0:
            if config['general']['warn_unmanaged']:
                LOGGER.warning(
                    "{} searches in app '{}' not being managed! "
                    "Offending search list: {}".format(
                        len(searchlist),
                        app,
                        searchlist
                    )
                )
            if app in config['general']['remove_unmanaged']:
                for search in searchlist:
                    try:
                        splunk.deleteSearch(app=app, searchName=search)
                        LOGGER.info(
                            "Search '{}' in app '{}' "
                            "deleted successfully.".format(
                                search,
                                app
                            )
                        )
                    except Exception as e:
                        LOGGER.error(
                            "Search '{}' in app '{}' could not "
                            "be deleted! {}".format(
                                search,
                                app,
                                e
                            )
                        )


def lambda_handler(event, context):
    if event.get('debug'):
        LOGGER.setLevel(logging.DEBUG)

    try:
        deploy()
        responseBody = {}

        response = {
            'statusCode': 200,
            'body': json.dumps(responseBody)
        }

    except Exception as error:
        LOGGER.error('error: {} '.format(
            getattr(error, 'message', repr(error))
        ))
        response = {
            'statusCode': 500,
            'body': json.dumps(
                {
                    'Error': 'Exception - {}'.format(
                        getattr(error, 'message', repr(error))
                    )
                }
            )
        }

    return response


def main():
    cli.banner()
    args = cli.parseArgs(VALID_COMMANDS)

    if args.debug:
        LOGGER.setLevel(logging.DEBUG)

    if not args.nojson:
        json_logging.init_non_web(enable_json=True)

    globals()[args.command]()


if __name__ == '__main__':
    main()
