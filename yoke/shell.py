import argparse
import base64
import boto3
import json
import logging
import os
import sys
import ruamel.yaml as yaml

import config
import deploy

LOG = logging.getLogger(__name__)


def decrypt(args):
    stage = args.stage
    stage_cfg = base64.b64decode(args.config['stages'][stage]['config'])
    region = args.config['stages'][stage]['region']
    kms = boto3.client('kms', region_name=region)
    resp = kms.decrypt(CiphertextBlob=bytes(stage_cfg))
    print('Decrypted config for stage {}:\n\n{}'.format(
        stage,
        yaml.round_trip_dump(json.loads(resp['Plaintext']))))


def deploy_app(args):
    deployment = deploy.Deployment(args.config)
    deployment.deploy_lambda()
    if args.config.get('apiGateway'):
        deployment.deploy_api()
    LOG.warning('Deployment complete!')


def encrypt(args):
    stage = args.config['stages'][args.stage]
    kms = boto3.client('kms', region_name=stage['region'])
    key_name = 'alias/{}'.format(stage['keyName'])
    resp = kms.encrypt(KeyId=key_name,
                       Plaintext=bytes(json.dumps(stage['config'])))
    print('Encrypted config for stage {}:\n\n{}'.format(
          args.stage,
          base64.b64encode(resp['CiphertextBlob'])))


def main(arv=None):
    parser = argparse.ArgumentParser(
        version='version 0.0.1',
        description='AWS Lambda + API Gateway Deployment Tool'
    )

    subparsers = parser.add_subparsers()

    parser.add_argument('--debug', dest='loglevel', help='Debug logging',
                        action='store_const', const=logging.DEBUG)
    parser.set_defaults(loglevel=logging.WARNING)

    deploy_parser = subparsers.add_parser('deploy')
    deploy_parser.add_argument('--stage', dest='stage', help='Stage to deploy',
                               default=os.getenv('YOKE_STAGE'))
    deploy_parser.add_argument('project_dir', default=os.getcwd(), nargs='?',
                               help='Project directory containing yoke.yml')
    deploy_parser.set_defaults(func=deploy_app)

    decrypt_parser = subparsers.add_parser('decrypt')
    decrypt_parser.add_argument('--stage', dest='stage',
                                help='Stage to deploy',
                                default=os.getenv('YOKE_STAGE'))
    decrypt_parser.add_argument('project_dir', default=os.getcwd(), nargs='?',
                                help='Project directory containing yoke.yml')
    decrypt_parser.set_defaults(func=decrypt)

    encrypt_parser = subparsers.add_parser('encrypt')
    encrypt_parser.add_argument('--stage', dest='stage',
                                help='Stage to deploy',
                                default=os.getenv('YOKE_STAGE'))
    encrypt_parser.add_argument('project_dir', default=os.getcwd(), nargs='?',
                                help='Project directory containing yoke.yml')
    encrypt_parser.set_defaults(func=encrypt)

    args = parser.parse_args()

    if args.loglevel is logging.WARNING:
        format = "%(message)s"
        logging.basicConfig(level=args.loglevel, format=format)
    else:
        logging.basicConfig(level=args.loglevel)

    try:
        args.project_dir = os.path.abspath(args.project_dir)
        _cfg = config.YokeConfig(args.project_dir, args.stage)
        args.config = _cfg.get_config()
        args.func(args)
    except Exception:
        LOG.exception('ERROR!')
        sys.exit(1)
