import base64
import json
import logging

import boto3
import ruamel.yaml as yaml
from six import string_types

LOG = logging.getLogger(__name__)


def check_encryption_required_fields(stage):
    for field in ['keyRegion', 'keyName']:
        if field not in stage:
            raise Exception("`{}` is a required field when secretConfig is "
                            "used.".format(field))


def decrypt(config, output=False):
    stage = config['stage']
    check_encryption_required_fields(config['stages'][stage])

    enc_config = get_secret_config(config, stage)
    if not isinstance(enc_config, string_types):
        raise Exception('Secret config for stage {} is not a '
                        'string! Did you forget to encrypt '
                        'first?'.format(stage))
    stage_cfg = base64.b64decode(enc_config)
    region = config['stages'][stage]['keyRegion']
    kms = boto3.client('kms', region_name=region)
    resp = kms.decrypt(CiphertextBlob=stage_cfg)
    plain = json.loads(resp['Plaintext'])
    if output:
        print('Decrypted config for stage {}:\n\n{}'.format(
            stage,
            yaml.round_trip_dump(plain)))
    return plain


def encrypt(config, output=False):
    stage = config['stages'][config['stage']]
    check_encryption_required_fields(stage)
    secret_config = get_secret_config(config, config['stage'])
    kms = boto3.client('kms', region_name=stage['keyRegion'])
    key_name = 'alias/{}'.format(stage['keyName'])
    resp = kms.encrypt(KeyId=key_name,
                       Plaintext=json.dumps(secret_config).encode('utf-8'))
    if output:
        print('Encrypted config for stage {}:\nsecretConfig: "{}"\n'.format(
            config['stage'],
            base64.b64encode(resp['CiphertextBlob']).decode('utf-8')))


def format_env(env_list):
    env_dict = {}
    for env_item in env_list:
        # A value might contain an '=' so let's not clobber that.
        parts = env_item.split('=')
        key = parts.pop(0)
        value = '='.join(parts)
        env_dict[key] = value
    return env_dict


def get_secret_config(config, stage):
    old_style = config['stages'][stage].get('secret_config')
    if old_style:
        LOG.warning('{} stage is using "secret_config" - please update to'
                    ' "secretConfig". This will break in the '
                    'future!'.format(stage))
    new_style = config['stages'][stage].get('secretConfig')
    if old_style and new_style:
        raise Exception('Please use only one of '
                        '"secretConfig" or "secret_config!"')
    return old_style if old_style else new_style


def retry_if_api_limit(exception):
    if 'TooManyRequestsException' in str(exception):
        LOG.warning('Hit API Gateway rate limit - retrying ...')
        return True
    return False
