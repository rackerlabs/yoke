from hashlib import sha1
import logging
import os
import subprocess
from tempfile import mkstemp
import time

import docker

from .templates import DOCKER_BUILD_SCRIPT
from .templates import DOCKER_INSTALL_SCRIPT

LOG = logging.getLogger(__name__)

BUILD_IMAGE = "quay.io/pypa/manylinux1_x86_64"
CONTAINER_POLL_INTERVAL = 10
PYTHON_VERSION_MAP = {
    # cp27-mu is compiled with ucs4 support which is the same as Lambda
    'python2.7': 'cp27-cp27mu',
    'python3.6': 'cp36-cp36m',
}
STATUS_EXITED = 'exited'


def wait_for_container_to_finish(container):
    while container.status != STATUS_EXITED:
        time.sleep(CONTAINER_POLL_INTERVAL)
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

    def __init__(self, runtime, project_path, wheelhouse_path, lambda_path,
                 install_dir, service_name, extra_packages=None,
                 build_openssl=False, build_libffi=False, build_libxml=False):
        """Initialize dependency builder object.

        :param runtime: Lambda Python runtime version.
        :param project_path: Full path to the project root, where `yoke.yml`
        exists.
        :param wheelhouse_path: Full path to the directory that will hold
        the build depdendencies (wheels).
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
        self.wheelhouse_path = wheelhouse_path
        self.lambda_path = lambda_path
        self.install_dir = install_dir
        self.service_name = service_name
        self.extra_packages = extra_packages or []
        self.build_openssl = build_openssl
        self.build_libffi = build_libffi
        self.build_libxml = build_libxml

    def should_rebuild(self):
        # There's a way to force rebuilding of dependencies
        if os.environ.get('FORCE_WHEEL_REBUILD') == 'true':
            LOG.warning(
                "FORCE_WHEEL_REBUILD env variable set, rebuilding "
                "dependencies.")
            return True
        # There's also a way to remove all existing dependencies, to force a
        # rebuild that way.
        sha1sum_file = os.path.join(self.wheelhouse_path, 'sha1sum')
        if os.environ.get('FORCE_WHEEL_CLEANUP') == 'true':
            LOG.warning(
                "FORCE_WHEEL_CLEANUP env variable set, cleaning up dependency "
                "directory.")
            wheel_pattern = os.path.join(self.wheelhouse_path, '*.whl')
            subprocess.call('rm -f {}'.format(wheel_pattern), shell=True)
            subprocess.call(['rm', '-f', sha1sum_file])

        if not os.path.isfile(sha1sum_file):
            LOG.warning(
                "SHA1 checksum file does not exist, rebuilding dependencies.")
            return True
        with open(sha1sum_file, 'r') as fp:
            sha1sum = fp.read().strip()

        requirements_file = os.path.join(self.lambda_path, 'requirements.txt')
        with open(requirements_file, 'r') as fp:
            calculated_sha1sum = sha1(fp.read().encode('utf-8')).hexdigest()

        if sha1sum != calculated_sha1sum:
            LOG.warning("SHA1 mismatch, rebuilding dependencies.")
            return True
        else:
            LOG.warning("SHA1 match, skip building dependencies.")
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
        build_script_path = self.generate_build_script()
        try:
            container = client.containers.run(
                image=BUILD_IMAGE,
                command='/bin/bash -c "./build_wheels.sh"',
                detach=True,
                environment={
                    'BUILD_OPENSSL': '1' if self.build_openssl else '0',
                    'BUILD_LIBFFI': '1' if self.build_libffi else '0',
                    'BUILD_LIBXML': '1' if self.build_libxml else '0',
                    'EXTRA_PACKAGES': ' '.join(self.extra_packages),
                    'PY_VERSION': PYTHON_VERSION_MAP[self.runtime],
                },
                volumes={
                    self.wheelhouse_path: {'bind': '/wheelhouse'},
                    self.lambda_path: {'bind': '/src'},
                    build_script_path: {'bind': '/build_wheels.sh'},
                },
            )
            LOG.warning(
                "Build container started, waiting for completion (ID: %s)",
                container.short_id,
            )
            wait_for_container_to_finish(container)
            LOG.warning("Build finished.")
            remove_container(container)
        finally:
            os.remove(build_script_path)

        self._install_dependencies(client)

    def _install_dependencies(self, docker_client):
        install_script_path = self.generate_install_script()
        try:
            project_path = os.path.dirname(self.lambda_path)
            container = docker_client.containers.run(
                image=BUILD_IMAGE,
                command='/bin/bash -c "./install_wheels.sh"',
                detach=True,
                environment={
                    'INSTALL_DIR': self.install_dir,
                    'PY_VERSION': PYTHON_VERSION_MAP[self.runtime],
                },
                volumes={
                    self.wheelhouse_path: {'bind': '/wheelhouse'},
                    project_path: {'bind': '/src'},
                    self.lambda_path: {'bind': '/lambda'},
                    install_script_path: {'bind': '/install_wheels.sh'},
                },
            )
            LOG.warning(
                "Install container started, waiting for completion (ID: %s)",
                container.short_id,
            )
            wait_for_container_to_finish(container)
            LOG.warning("Install finished.")
            remove_container(container)
        finally:
            os.remove(install_script_path)

    def _generate_script(self, contents):
        # Place temporary file inside `/tmp`, because Docker for Mac only
        # allows mounting volumes from certain locations, and the default temp
        # directory is not among them.
        fd, filename = mkstemp(suffix='.sh', dir='/tmp')
        os.close(fd)
        with open(filename, 'w') as fp:
            fp.write(contents)

        os.chmod(filename, 0o755)
        return filename

    def generate_build_script(self):
        return self._generate_script(DOCKER_BUILD_SCRIPT)

    def generate_install_script(self):
        return self._generate_script(DOCKER_INSTALL_SCRIPT)
