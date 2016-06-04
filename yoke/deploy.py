import boto3
from collections import namedtuple, OrderedDict
from jinja2 import Environment, FileSystemLoader
from lambda_uploader import package, uploader
import logging
import json
import os

LOG = logging.getLogger(__name__)

API_GATEWAY_URL_TEMPLATE = "https://{}.execute-api.{}.amazonaws.com/{}"


class Deployment(object):

    def __init__(self, config):
        self.config = config
        self.project_dir = self.config['project_dir']
        self.stage = config['stage']
        self.region = self.config['stages'][self.stage]['region']
        self.lambda_path = os.path.join(self.project_dir,
                                        self.config['Lambda']['path'])
        self.account_id = config['account_id']
        # Let's make sure the accounts match up
        self.verify_account_id()

    def build_lambda_package(self):
        LOG.warning("Building Lambda package ...")
        pkg = package.build_package(self.lambda_path, None)
        pkg.clean_workspace()
        return pkg

    def create_upldr_config(self):
        Lambda = self.config['Lambda']
        Lambda['config']['s3_bucket'] = None
        Lambda['config']['publish'] = True
        Lambda['config']['alias'] = self.stage
        Lambda['config']['alias_description'] = Lambda['config']['description']
        Lambda['config']['region'] = self.region
        ordered = OrderedDict(sorted(Lambda['config'].items(),
                                     key=lambda x: x[1]))
        upldr_config = namedtuple('config', ordered.keys())(**ordered)
        return upldr_config

    def deploy_lambda(self):
        self.write_lambda_json()
        self.write_lambda_config()
        pkg = self.build_lambda_package()

        # Create fake config for lambda uploader because
        # it isn't completely ok with being used as a library.
        upldr_config = self.create_upldr_config()

        # Upload lambda
        self.upload_lambda(pkg, upldr_config)

    def deploy_api(self):

        # Template swagger.yml from template
        template = self.render_swagger()
        swagger_file = self.write_template(template)

        # Import/Update API from swagger.yml
        api = self.upload_api(swagger_file)
        LOG.warning("Deploying API to %s stage ...", self.stage)
        client = boto3.client('apigateway', region_name=self.region)
        deployment = client.create_deployment(
            restApiId=api['id'],
            stageName=self.stage)
        LOG.warning("API deployed! URL:\n %s",
                    API_GATEWAY_URL_TEMPLATE.format(api['id'],
                                                    self.region,
                                                    self.stage))
        return deployment

    def render_swagger(self):
        LOG.warning("Templating swagger.yml for region %s ...", self.region)
        swagger_file = self.config['apiGateway'].get('swaggerTemplate',
                                                     'template.yml')
        j2_env = Environment(loader=FileSystemLoader(self.project_dir),
                             trim_blocks=True, lstrip_blocks=True)
        rendered_template = j2_env.get_template(swagger_file).render(
            accountId=self.account_id,
            Lambda=self.config['Lambda'],
            apiGateway=self.config['apiGateway'],
            region=self.region,
            stage=self.stage
        )
        return rendered_template

    def upload_api(self, swagger_file):
        LOG.warning("Uploading API to AWS Account %s for region %s ...",
                    self.account_id, self.region)
        client = boto3.client('apigateway', region_name=self.region)

        # Try to find API by name
        apis = client.get_rest_apis()
        apis = apis.get('items')
        api = None
        for item in apis:
            if self.config['apiGateway']['name'] == item['name']:
                LOG.warning('Found existing API: %s', item['name'])
                api = item
                break
        with open(swagger_file, 'r') as import_file:
            upload_body = import_file.read()

        if api:
            LOG.warning("API %s already exists - updating ...", api['name'])
            api = client.put_rest_api(restApiId=api['id'], body=upload_body)
        else:
            LOG.warning("API %s not found, importing ...",
                        self.config['apiGateway']['name'])
            api = client.import_rest_api(body=upload_body)

        return api

    def upload_lambda(self, pkg, upldr_config):
        LOG.warning("Uploading Lambda %s to AWS Account %s "
                    "for region %s ...",
                    upldr_config.name, self.account_id, upldr_config.region)
        uploader.PackageUploader._format_vpc_config = self._format_vpc_config
        upldr = uploader.PackageUploader(upldr_config, None)
        upldr.upload(pkg)
        upldr.alias()
        pkg.clean_zipfile()

    def verify_account_id(self):
        LOG.warning('Verifying AWS Account Credentials ...')
        aws_account_id = boto3.client('iam').list_users(MaxItems=1)[
            'Users'][0]['Arn'].split(':')[4]
        try:
            assert aws_account_id == self.account_id
        except Exception:
            LOG.error('yoke.yml accountId (%s) does not match credentials'
                      'account (%s)!', self.account_id, aws_account_id)
            raise

    def write_lambda_config(self):
        lambda_config = self.config['stages'][self.stage].get('config')
        if lambda_config:
            config_file = os.path.join(self.lambda_path,
                                       'config.json')
            with open(config_file, 'w') as outfile:
                json.dump(lambda_config, outfile)

    def write_lambda_json(self):
        lambda_json = os.path.join(self.lambda_path,
                                   'lambda.json')
        with open(lambda_json, 'w') as outfile:
            json.dump(self.config['Lambda']['config'], outfile)

    def write_template(self, output):
        swagger_file = os.path.join(self.project_dir, 'swagger.yml')
        with open(swagger_file, 'w') as fh:
            fh.write(output)
        return swagger_file

    def _format_vpc_config(self):

        # todo(ryandub): Add VPC support
        return {}
