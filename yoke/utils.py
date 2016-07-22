import base64
import json

import boto3
import ruamel.yaml as yaml


def decrypt(config, output=False):
    stage = config['stage']
    stage_cfg = base64.b64decode(config['stages'][stage]['secret_config'])
    region = config['stages'][stage]['keyRegion']
    kms = boto3.client('kms', region_name=region)
    resp = kms.decrypt(CiphertextBlob=bytes(stage_cfg))
    plain = json.loads(resp['Plaintext'])
    if output:
        print('Decrypted config for stage {}:\n\n{}'.format(
            stage,
            yaml.round_trip_dump(plain)))
    return plain


def encrypt(config, output=False):
    stage = config['stages'][config['stage']]
    kms = boto3.client('kms', region_name=stage['keyRegion'])
    key_name = 'alias/{}'.format(stage['keyName'])
    resp = kms.encrypt(KeyId=key_name,
                       Plaintext=bytes(json.dumps(stage['config'])))
    if output:
        print('Encrypted config for stage {}:\n\n{}'.format(
              config['stage'],
              base64.b64encode(resp['CiphertextBlob'])))
