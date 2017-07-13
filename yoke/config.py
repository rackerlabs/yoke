import boto3
from botocore.exceptions import ClientError
import json
import logging
import os
import re
import ruamel.yaml as yaml

from . import utils

LOG = logging.getLogger(__name__)
LAMBDA_ROLE_ARN_TEMPLATE = "arn:aws:iam::{account_id}:role/{role}"


class YokeConfig(object):

    def __init__(self, shellargs, project_dir, stage, env_dict):
        self._args = shellargs
        self.project_dir = project_dir
        self.stage = stage
        self.env_dict = env_dict
        self.yoke_path = os.path.join(self.project_dir, 'yoke.yml')

    def check_default_stage(self, config, stage):
        # Set provided stage's config to default configs
        if stage == 'default':
            config['stages'][self.stage] = config['stages'][stage]
            # If you don't have a default config, initialize it.
            if not config['stages'][self.stage].get('config'):
                config['stages'][stage]['config'] = {}
            stage = self.stage
        config['stage'] = self.stage
        return config

    def get_config(self, skip_decrypt=False):
        config = self.load_config_file()
        stage = self.get_stage(self.stage, config)
        config = self.check_default_stage(config, stage)

        config['project_dir'] = self.project_dir
        config['account_id'] = self.get_account_id()

        if 'config' not in config['stages'][self.stage]:
            config['stages'][self.stage]['config'] = {}

        if not skip_decrypt:
            if (config['stages'][self.stage].get('secret_config') or
                    config['stages'][self.stage].get('secretConfig')):
                dec_config = utils.decrypt(config)
                config['stages'][self.stage]['config'].update(dec_config)

        if self.env_dict:
            config['stages'][self.stage]['config'].update(self.env_dict)

        # Set proper Lambda ARN for role
        config['Lambda']['config']['role'] = LAMBDA_ROLE_ARN_TEMPLATE.format(
            account_id=config['account_id'],
            role=config['Lambda']['config']['role']
        )

        LOG.info('Config:\n%s', json.dumps(config, indent=4))

        return config

    def get_stage(self, stage, config):
        assert stage, "No YOKE_STAGE envvar found - aborting!"
        LOG.warning("Loading stage %s ...", stage)
        if not config['stages'].get(stage):
            if not config['stages'].get('default'):
                LOG.warning('%s stage was not found and no default '
                            'stage was provided - aborting!', stage)
                raise
            LOG.warning("%s stage was not found - using default ...", stage)
            stage = 'default'
        return stage

    def get_account_id(self):
        LOG.warning('Getting AWS Account Credentials ...')
        try:
            aws_account_id = boto3.client('iam').get_user()[
                'User']['Arn'].split(':')[4]
        except ClientError as exc:
            LOG.debug("Failed to get account via get_user()...\n %s",
                      str(exc))
            aws_account_id = boto3.client('sts').get_caller_identity()[
                'Account']

        return str(aws_account_id)

    def load_config_file(self):
        # Read config file lines as list in order to template.
        LOG.warning("Getting config from %s ...", self.project_dir)
        with open(self.yoke_path, 'r') as config_file:
            raw = config_file.readlines()
        raw = self.render_config(raw)
        return yaml.safe_load(raw)

    def render_config(self, config):
        vars = self.env_dict
        vars['stage'] = self.stage
        rendered = []
        p = re.compile(".*?\{\{ (.*?) \}\}.*?")
        for line in config:
            match = p.findall(line)
            for var in match:
                replace_var = self.env_dict[var]
                line = line.replace("{{{{ {} }}}}".format(var),
                                    replace_var, 1)
            rendered.append(line)
        LOG.debug("Rendered config:\n{}".format(rendered))
        return ''.join(rendered)
