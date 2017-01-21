import argparse
import logging
import os
import sys

import config
import deploy
import utils

LOG = logging.getLogger(__name__)


def build(args):
    LOG.warning('Building deployment only ...')
    deployment = deploy.Deployment(args.config)
    deployment.write_lambda_json()
    deployment.write_lambda_config()
    if args.config.get('apiGateway'):
        template = deployment.render_swagger()
        swagger_file = deployment.write_template(template)
        # Also write the deref'd JSON version
        deployment.deref(template)
        LOG.warning('API Gateway Swagger file written to {}'.format(
                    swagger_file))


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

    deploy_parser = subparsers.add_parser(
        'deploy',
        help='Deploy lambda and (optionally) API Gateway.')
    deploy_parser.add_argument('--stage', dest='stage', help='Stage to deploy',
                               default=os.getenv('YOKE_STAGE'))
    deploy_parser.add_argument('--environment', '-e', dest='environment',
                               help=('Extra config values for lambda '
                                     'config - can be used multiple times'),
                               default=[], action='append',
                               metavar='KEYNAME=VALUE')
    deploy_parser.add_argument('project_dir', default=os.getcwd(), nargs='?',
                               help='Project directory containing yoke.yml')
    deploy_parser.set_defaults(func=deploy_app)

    deploy_parser = subparsers.add_parser(
        'build',
        help='Only template config files and build lambda package.')
    deploy_parser.add_argument('--stage', dest='stage', help='Stage to build',
                               default=os.getenv('YOKE_STAGE'))
    deploy_parser.add_argument('--environment', '-e', dest='environment',
                               help=('Extra config values for lambda '
                                     'config - can be used multiple times'),
                               default=[], action='append',
                               metavar='KEYNAME=VALUE')
    deploy_parser.add_argument('project_dir', default=os.getcwd(), nargs='?',
                               help='Project directory containing yoke.yml')
    deploy_parser.set_defaults(func=build)

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
        logging.basicConfig(level=args.loglevel, format=format,
                            stream=sys.stdout)
    else:
        logging.basicConfig(level=args.loglevel, stream=sys.stdout)

    try:
        args.project_dir = os.path.abspath(args.project_dir)
        if hasattr(args, 'environment'):
            env_dict = utils.format_env(args.environment)
        else:
            env_dict = {}
        _cfg = config.YokeConfig(args, args.project_dir, args.stage, env_dict)
        args.config = _cfg.get_config()
        args.func(args)
    except Exception:
        LOG.exception('ERROR!')
        sys.exit(1)
