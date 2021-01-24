from cerberus import Validator
from benedict import benedict

from exceptions import ConfigValidateFailed


def getValidSearch(config):
    '''
    Validates a search definition, removing unknown values
    Returns: Validated document after purge
    '''
    schema = benedict.from_json('src/schemas/search.json')
    v = Validator(schema, purge_unknown=True)
    validated = {}
    for searchname, search in config.items():
        if not (v.validate(search)):
            raise ConfigValidateFailed(
                "Validation of search '{}' failed! Error(s): {}".format(
                    searchname,
                    v.errors
                )
            )
        validated[searchname] = v.document

    return validated


def validateConfig(config, schemafile):
    '''
    Validates a search definition, removing unknown values
    Returns: Validated document after purge
    '''
    schema = benedict.from_json(schemafile)
    v = Validator(schema)
    if not (v.validate(config)):
        raise ConfigValidateFailed(
            "Validation of SAD config failed! Error(s): {}".format(
                v.errors
            )
        )
