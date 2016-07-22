import argparse
import logging
import os
import sys

import config
import deploy
import utils

LOG = logging.getLogger(__name__)


def decrypt(args):
    utils.decrypt(args.config, output=True)


def deploy_app(args):
    deployment = deploy.Deployment(args.config)
    deployment.deploy_lambda()
    if args.config.get('apiGateway'):
        deployment.deploy_api()
    LOG.warning('Deployment complete!')


def encrypt(args):
    utils.encrypt(args.config, output=True)


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
    deploy_parser.add_argument('--environment', '-e', dest='environment',
                               help=('Extra config values for lambda'
                                     'environment. Format: KEYNAME=VALUE',),
                               default=[], action='append')
    deploy_parser.add_argument('project_dir', default=os.getcwd(), nargs='?',
                               help='Project directory containing yoke.yml')
    deploy_parser.set_defaults(func=deploy_app)

    decrypt_parser = subparsers.add_parser('decrypt')
    decrypt_parser.add_argument('--stage', dest='stage',
                                help='Stage to decrypt',
                                default=os.getenv('YOKE_STAGE'))
    decrypt_parser.add_argument('project_dir', default=os.getcwd(), nargs='?',
                                help='Project directory containing yoke.yml')
    decrypt_parser.set_defaults(func=decrypt)

    encrypt_parser = subparsers.add_parser('encrypt')
    encrypt_parser.add_argument('--stage', dest='stage',
                                help='Stage to encrypt',
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
        env_dict = utils.format_env(args.environment)
        _cfg = config.YokeConfig(args.project_dir, args.stage, env_dict)
        args.config = _cfg.get_config()
        args.func(args)
    except Exception:
        LOG.exception('ERROR!')
        sys.exit(1)
