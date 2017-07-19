import argparse
import logging
import os
import sys

from . import config
from . import deploy
from . import utils

LOG = logging.getLogger(__name__)


def build(args):
    deploy.build(args.config)


def build_dependencies(args):
    deploy.build_dependencies(args.config)


def decrypt(args):
    utils.decrypt(args.config, output=True)


def deploy_app(args):
    deploy.deploy_app(args.config)


def encrypt(args):
    utils.encrypt(args.config, output=True)


def main(arv=None):
    parser = argparse.ArgumentParser(
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

    build_parser = subparsers.add_parser(
        'build',
        help='Only template config files and build lambda package.')
    build_parser.add_argument('--stage', dest='stage', help='Stage to build',
                              default=os.getenv('YOKE_STAGE'))
    build_parser.add_argument('--environment', '-e', dest='environment',
                              help=('Extra config values for lambda '
                                    'config - can be used multiple times'),
                              default=[], action='append',
                              metavar='KEYNAME=VALUE')
    build_parser.add_argument('project_dir', default=os.getcwd(), nargs='?',
                              help='Project directory containing yoke.yml')
    build_parser.set_defaults(func=build)

    build_dependencies_parser = subparsers.add_parser(
        'build-dependencies',
        help='Build service dependencies.')
    build_dependencies_parser.add_argument(
        '--environment', '-e', dest='environment',
        help='Extra config values for lambda config - can be used multiple '
             'times',
        default=[], action='append',
        metavar='KEYNAME=VALUE')
    build_dependencies_parser.add_argument(
        'project_dir', default=os.getcwd(),
        nargs='?',
        help='Project directory containing yoke.yml')
    build_dependencies_parser.set_defaults(func=build_dependencies)

    decrypt_parser = subparsers.add_parser(
        'decrypt',
        help='Decrypt secrets stored in yoke.yml.')
    decrypt_parser.add_argument('--stage', dest='stage',
                                help='Stage to decrypt',
                                default=os.getenv('YOKE_STAGE'))
    decrypt_parser.add_argument('project_dir', default=os.getcwd(), nargs='?',
                                help='Project directory containing yoke.yml')
    decrypt_parser.set_defaults(func=decrypt)

    encrypt_parser = subparsers.add_parser(
        'encrypt',
        help='Encrypt secrets just added in plain-text to yoke.yml')
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
        # Some commands (currently: build-dependencies) don't require a stage
        # to work, so let's just fake one here to make sure things continue to
        # work.
        if not hasattr(args, 'stage'):
            args.stage = 'nostage'
        _cfg = config.YokeConfig(args, args.project_dir, args.stage, env_dict)
        skip_decrypt = args.func.__name__ in (
            'build_dependencies',
            'encrypt',
            'decrypt',
        )
        args.config = _cfg.get_config(skip_decrypt=skip_decrypt)
        args.func(args)
    except Exception:
        LOG.exception('ERROR!')
        sys.exit(1)
