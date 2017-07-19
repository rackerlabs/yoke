from collections import namedtuple, OrderedDict
import copy
import logging
import json
import os
import re

import boto3
from botocore.exceptions import ClientError
from jinja2 import Environment, DictLoader, FileSystemLoader
import jsonref
from lambda_uploader import package, uploader
from retrying import retry
import ruamel.yaml as yaml

from .build_deps import PythonDependencyBuilder
from . import templates
from . import utils

LOG = logging.getLogger(__name__)

API_GATEWAY_URL_TEMPLATE = "https://{}.execute-api.{}.amazonaws.com/{}"


def build(config):
    LOG.warning('Building deployment only ...')
    deployment = Deployment(config)
    deployment.write_lambda_json()
    deployment.write_lambda_config()
    if config.get('apiGateway'):
        template = deployment.render_swagger()
        swagger_file = deployment.write_template(template)
        # Also write the deref'd JSON version
        deployment.deref(template)
        LOG.warning('API Gateway Swagger file written to {}'.format(
                    swagger_file))

    deployment.build_lambda_package()


def build_dependencies(config):
    LOG.warning('Building dependencies only ...')
    deployment = Deployment(config)
    deployment.build_dependencies()


def deploy_app(config):
    deployment = Deployment(config)
    deployment.deploy_lambda()
    if config.get('apiGateway'):
        deployment.deploy_api()
    LOG.warning('Deployment complete!')


class Deployment(object):

    def __init__(self, config):
        self.config = config
        self.project_dir = self.config['project_dir']
        self.stage = config['stage']
        self.region = self.config['stages'][self.stage]['region']
        self.lambda_path = os.path.abspath(os.path.join(self.project_dir,
                                           self.config['Lambda']['path']))
        self.account_id = config['account_id']
        self.extra_files = self.normalize_extra_files(config['Lambda'])
        # Let's make sure the accounts match up
        self.verify_account_id()

    def apply_templates(self, template):
        aws_int = 'x-amazon-apigateway-integration'
        paths = template.get('paths')
        for path, methods in paths.items():
            for method, _config in methods.items():
                if _config.get('x-yoke-integration'):
                    template['paths'][path][method][
                        aws_int] = self.template_aws_integration(
                            _config['x-yoke-integration'])
        return template

    def build_dependencies(self):
        dependency_config = self.config['Lambda'].get('dependencies')
        if dependency_config is None:
            LOG.warning(
                "The 'dependencies' section in the 'Lambda' config does not "
                "exist, skipping the build of dependencies.")
        else:
            build_enabled = dependency_config.get('build', False)
            if not build_enabled:
                LOG.warning(
                    "Builds are not enabled for dependencies in the config.")
            else:
                LOG.warning("Building dependencies enabled ...")
                runtime = self.config['Lambda']['config'].get(
                    'runtime', 'python2.7')
                if not runtime.startswith('python'):
                    raise Exception(
                        "Building dependencies only supported on Python "
                        "runtimes."
                    )
                service_name = self.config['Lambda']['config']['name']
                wheelhouse_path = dependency_config.get('wheelhouse')
                if wheelhouse_path is not None:
                    wheelhouse_path = os.path.abspath(
                        os.path.join(
                            wheelhouse_path,
                            service_name,
                        ),
                    )
                else:
                    wheelhouse_path = os.path.abspath(
                        os.path.join(
                            self.project_dir,
                            '../../wheelhouse',
                            service_name,
                        ),
                    )
                install_dir = dependency_config.get('install_dir') or './lib'
                builder = PythonDependencyBuilder(
                    runtime=runtime,
                    project_path=self.project_dir,
                    wheelhouse_path=wheelhouse_path,
                    lambda_path=self.lambda_path,
                    install_dir=install_dir,
                    service_name=service_name,
                    extra_packages=dependency_config.get('packages'),
                    build_openssl=dependency_config.get('openssl', False),
                    build_libffi=dependency_config.get('libffi', False),
                    build_libxml=dependency_config.get('libxml', False),
                )
                builder.build()

    def build_lambda_package(self, skip_if_exists=False):
        LOG.warning("Building Lambda package ...")
        pkg = package.Package(self.lambda_path)
        pkg._requirements_file = None
        if os.path.isfile(pkg.zip_file):
            if skip_if_exists:
                # Package already built, don't do anything else
                LOG.warning(
                    "Lambda package already built, using existing file.")
                return pkg
            else:
                # Otherwise we should delete the existing file, otherwise it
                # will be packaged up.
                LOG.warning("Removing existing Lambda package.")
                os.remove(pkg.zip_file)

        # Leaving this here for backward-compatibility reasons. More recent
        # versions of Yoke might want to call the `build-dependencies` command
        # separately. If that's the case, this code below will not do too much,
        # because the built packages already exist and are up-to-date.
        self.build_dependencies()

        if self.extra_files:
            for _file in self.extra_files:
                pkg.extra_file(_file)
        pkg._prepare_workspace()
        pkg.package()
        pkg.clean_workspace()
        return pkg

    def create_upldr_config(self):
        Lambda = self.config['Lambda']
        Lambda['config']['s3_bucket'] = None
        Lambda['config']['publish'] = True
        Lambda['config']['alias'] = self.stage
        Lambda['config']['alias_description'] = Lambda['config']['description']
        Lambda['config']['region'] = self.region
        Lambda['config']['runtime'] = Lambda['config'].get('runtime',
                                                           'python2.7')
        Lambda['config']['variables'] = {}
        Lambda['config']['raw'] = {'vpc': Lambda['config'].get('vpc')}
        if not Lambda['config'].get('tracing'):
            Lambda['config']['tracing'] = {}
        ordered = OrderedDict(sorted(Lambda['config'].items(),
                                     key=lambda x: str(x[1])))
        upldr_config = namedtuple('config', ordered.keys())(**ordered)
        return upldr_config

    def deploy_lambda(self):
        self.write_lambda_json()
        self.write_lambda_config()
        pkg = self.build_lambda_package(skip_if_exists=True)

        # Create fake config for lambda uploader because
        # it isn't completely ok with being used as a library.
        upldr_config = self.create_upldr_config()

        # Upload lambda
        self.upload_lambda(pkg, upldr_config)

    @retry(retry_on_exception=utils.retry_if_api_limit,
           wait_exponential_multiplier=5000, wait_exponential_max=25000,
           stop_max_attempt_number=10)
    def deploy_api(self):

        # Template swagger.yml from template
        template = self.render_swagger()
        self.write_template(template)

        # Import/Update API from swagger.yml
        # Convert to JSON and deref for AWS API compatibility.
        upload_body = self.deref(template)
        api = self.upload_api(upload_body)
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

    def normalize_extra_files(self, lambda_config):
        normalized = []
        extra_files = lambda_config.get('extraFiles', [])
        for extra_file in extra_files:
            normalized.append(os.path.join(self.project_dir, extra_file))
        return normalized

    def render_swagger(self):
        LOG.warning("Templating swagger.yml for region %s ...", self.region)
        swagger_file = self.config['apiGateway'].get('swaggerTemplate',
                                                     'template.yml')
        j2_env = Environment(loader=FileSystemLoader(self.project_dir),
                             trim_blocks=True, lstrip_blocks=True)
        first_template = yaml.safe_load(
            j2_env.get_template(swagger_file).render(
                accountId=self.account_id,
                Lambda=self.config['Lambda'],
                apiGateway=self.config['apiGateway'],
                region=self.region,
                stage=self.stage))

        integrations_template = self.apply_templates(first_template)

        # We have to do this twice to template the integrations - I'm sorry.
        j2_env = Environment(loader=DictLoader(
            {'template': json.dumps(integrations_template)}))
        j2_template = j2_env.get_template('template')
        rendered_template = yaml.safe_load(j2_template.render(
            accountId=self.account_id,
            Lambda=self.config['Lambda'],
            apiGateway=self.config['apiGateway'],
            region=self.region,
            stage=self.stage
        ))

        return rendered_template

    def template_aws_integration(self, yoke_integration):
        integ = copy.deepcopy(templates.AWS_INTEGRATION)
        location = 'requestTemplates'
        content_type = 'application/json'
        integ[location] = copy.deepcopy(templates.DEFAULT_REQUESTS)
        integ[location][content_type] = self.template_operation(
            integ['requestTemplates']['application/json'],
            yoke_integration.get('operation'),
        )
        integ['responses'] = copy.deepcopy(templates.DEFAULT_RESPONSES)
        return integ

    def template_operation(self, template, operation):
        p = re.compile(".*?\{\{ (.*?) \}\}.*?")
        match = p.findall(template)
        for var in match:
            template = template.replace("{{{{ {} }}}}".format(var),
                                        operation, 1)
        return template

    def upload_api(self, upload_body):
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

        parameters = {'basepath': 'prepend'}
        if api:
            LOG.warning("API %s already exists - updating ...", api['name'])
            api = client.put_rest_api(restApiId=api['id'],
                                      mode='overwrite',
                                      body=json.dumps(upload_body),
                                      parameters=parameters)
        else:
            LOG.warning("API %s not found, importing ...",
                        self.config['apiGateway']['name'])
            api = client.import_rest_api(body=json.dumps(upload_body),
                                         parameters=parameters)

        return api

    def upload_lambda(self, pkg, upldr_config):
        LOG.warning("Uploading Lambda %s to AWS Account %s "
                    "for region %s ...",
                    upldr_config.name, self.account_id, upldr_config.region)
        upldr = uploader.PackageUploader(upldr_config, None)
        upldr.upload(pkg)
        upldr.alias()
        pkg.clean_zipfile()

    def verify_account_id(self):
        LOG.warning('Verifying AWS Account Credentials ...')

        try:
            aws_account_id = boto3.client('iam').get_user()[
                'User']['Arn'].split(':')[4]
        except ClientError:
            aws_account_id = boto3.client('sts').get_caller_identity()[
                'Account']
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

    def write_template(self, output, filename=None):
        if not filename:
            filename = 'swagger.yml'
        swagger_file = os.path.join(self.project_dir, filename)
        _, ext = os.path.splitext(filename)
        with open(swagger_file, 'w') as fh:
            # Could be `.yaml` or `.yml` :/
            if '.y' in ext:
                fh.write(yaml.round_trip_dump(output))
            elif '.json' in ext:
                fh.write(json.dumps(output))
        return swagger_file

    def deref(self, data):
        """AWS doesn't quite have Swagger 2.0 validation right and will fail
        on some refs. So, we need to convert to deref before
        upload."""

        # We have to make a deepcopy here to create a proper JSON
        # compatible object, otherwise `json.dumps` fails when it
        # hits jsonref.JsonRef objects.
        deref = copy.deepcopy(jsonref.JsonRef.replace_refs(data))

        # Write out JSON version because we might want this.
        self.write_template(deref, filename='swagger.json')

        return deref
