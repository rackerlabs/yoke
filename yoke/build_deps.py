from hashlib import sha1
from io import BytesIO
import logging
import os
import shutil
import subprocess
import tempfile
import time
import zipfile

import docker

from .templates import DOCKERFILE

LOG = logging.getLogger(__name__)

BUILD_IMAGE = "amazonlinux"
CONTAINER_POLL_INTERVAL = 10
FEEDBACK_IN_SECONDS = 60
STATUS_EXITED = 'exited'


def wait_for_container_to_finish(container):
    elapsed = 0
    while container.status != STATUS_EXITED:
        time.sleep(CONTAINER_POLL_INTERVAL)
        # Make sure we give some feedback to the user, that things are actually
        # happening in the background. Also, some CI systems detect the lack of
        # output as a build failure, which we'd like to avoid.
        elapsed += CONTAINER_POLL_INTERVAL
        if elapsed % FEEDBACK_IN_SECONDS == 0:
            LOG.warning("Container still running, please be patient...")

        container.reload()

    exit_code = container.attrs['State']['ExitCode']
    if exit_code != 0:
        # Save logs for further inspection -- if we are on CircleCI, save the
        # file under the artifacts directory.
        basepath = (
            os.environ['CIRCLE_ARTIFACTS']
            if 'CIRCLECI' in os.environ
            else '.'
        )
        log_filename = os.path.join(
            basepath,
            'container_{}.log'.format(container.short_id),
        )
        log_contents = container.logs(stdout=True, stderr=True)
        with open(log_filename, 'w') as fp:
            try:
                fp.write(log_contents)
            except TypeError:
                # On Python 3, `fp.write()` expects a string instead of bytes
                # (which is coming out of the `logs()` call), but Python 2
                # can't handle writing unicode to a file, so we can't do this
                # in both cases.
                fp.write(log_contents.decode('utf-8'))

        raise Exception(
            "Container exited with non-zero code. Logs saved to {}".format(
                log_filename)
        )


def remove_container(container):
    try:
        container.remove()
    except:
        # We just log an error and swallow the exception, because this happens
        # often on CircleCI.
        LOG.error(
            "Could not remove container, please remove it manually (ID: %s)",
            container.short_id,
        )


class PythonDependencyBuilder(object):

    def __init__(self, runtime, project_path, deps_cache_path, lambda_path,
                 install_dir, service_name, extra_packages=None):
        """Initialize dependency builder object.

        :param runtime: Lambda Python runtime version.
        :param project_path: Full path to the project root, where `yoke.yml`
        exists.
        :param deps_cache_path: Full path to the directory that will hold
        the build depdendencies.
        :param lambda_path: Full path to the directory where the Lambda
        function's code lives.
        :param install_dir: Relative path within the project root where the
        dependencies will be installed.
        :param service_name: Name of the service, used for creating some
        sub-directories and files.
        :param extra_packages: List of extra CentOS packages that should be
        installed before the dependencies are built.
        """
        self.runtime = runtime
        self.project_path = project_path
        self.deps_cache_path = deps_cache_path
        self.lambda_path = lambda_path
        self.install_dir = install_dir
        self.service_name = service_name
        self.extra_packages = extra_packages or []
        self.requirements_file = os.path.join(
            self.lambda_path,
            'requirements.txt'
        )
        self.requirements_sha = self._get_requirements_sha()
        self.deps_file = os.path.join(
            self.deps_cache_path,
            '{}.zip'.format(self.requirements_sha)
        )

    def should_rebuild(self):
        # There's a way to force rebuilding of dependencies
        if os.environ.get('FORCE_DEPS_REBUILD') == 'true':
            LOG.warning(
                "FORCE_DEPS_REBUILD env variable set, rebuilding "
                "dependencies.")
            return True

        # There's also a way to remove all existing dependencies, to force a
        # rebuild that way.
        if os.environ.get('FORCE_DEPS_CLEANUP') == 'true':
            LOG.warning(
                "FORCE_DEPS_CLEANUP env variable set, cleaning up dependency "
                "directory.")
            deps_pattern = os.path.join(self.deps_cache_path, '*.zip')
            subprocess.call('rm -f {}'.format(deps_pattern), shell=True)

        if not os.path.isfile(self.deps_file):
            LOG.warning("Dependency archive does not exist, "
                        "rebuilding depdendencies.")
            return True
        else:
            LOG.warning("Dependency archive found, "
                        "skip building dependencies.")
            return False

    def build(self):
        try:
            # Allow connecting to older Docker versions (e.g. CircleCI 1.0)
            client = docker.from_env(version='auto')
        except:
            LOG.error("Docker is not running, or it's outdated.")
            raise

        if not self.should_rebuild():
            # Even if we don't have to rebuild the dependencies, we still have
            # to install them, so that they can be picked up into the bundle.
            self._install_dependencies(client)
            return

        # Build dependencies
        docker_file = BytesIO(DOCKERFILE.encode('ascii'))
        image = client.images.build(
            fileobj=docker_file,
            tag='yokelambdabuilder',
            buildargs={
                'python_version': self.runtime,
                'deps': self.extra_packages,
            },
        )

        # There is no context manager for mkdtemp in Python 2.7 :(
        build_dir = tempfile.mkdtemp(dir='/tmp')
        try:
            container = client.containers.run(
                image=image.tags[0],
                detach=True,
                volumes={
                    build_dir: {'bind': '/out'},
                    self.requirements_file: {'bind': '/src/requirements.txt'},
                },
            )
            LOG.warning(
                "Build container started, waiting for completion (ID: %s)",
                container.short_id,
            )
            wait_for_container_to_finish(container)
            LOG.warning("Build finished.")
            remove_container(container)

            self._package_deps(build_dir)
        finally:
            try:
                shutil.rmtree(build_dir)
            # CircleCI does not allow you to remove things in /tmp for some
            # reason.
            except OSError as exc:
                LOG.warning("Failed to remove build directory - {}".format(
                    build_dir))
                LOG.debug(str(exc))

        self._install_dependencies(client)

    def _get_requirements_sha(self):
        with open(self.requirements_file, 'r') as fp:
            calculated_sha1sum = sha1(fp.read().encode('utf-8')).hexdigest()
        return calculated_sha1sum

    def _package_deps(self, build_dir):
        LOG.warning('Packaging up dependencies.')
        deps_archive = shutil.make_archive(
            os.path.join(self.deps_cache_path, self.requirements_sha),
            'zip',
            build_dir,
        )
        LOG.warning('Dependency archive created: {}.'.format(deps_archive))

    def _install_dependencies(self, docker_client):
        if not os.path.exists(self.install_dir):
            LOG.warning('Install directory does not exist, creating.')
            os.makedirs(self.install_dir)
            LOG.warning('Created install directory {}.'.format(
                self.install_dir))

        with zipfile.ZipFile(self.deps_file, 'r') as zip_file:
            zip_file.extractall(self.install_dir)

        LOG.warning('Installed dependencies to {}.'.format(self.install_dir))
