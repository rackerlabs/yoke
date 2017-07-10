import ast
import re
from setuptools import setup, find_packages


INSTALL_REQUIRES = [
    'boto3>=1.4.2',
    'botocore>=1.4.85',
    'docker>=2.0.0',
    'Jinja2>=2.8',
    'jsonref>=0.1',
    'lambda-uploader>=1.2.0',
    'retrying>=1.3.3',
    'ruamel.yaml>=0.11.11',
    'six>=1.10.0',
]


def package_meta():
    """Read __init__.py for global package metadata.
    Do this without importing the package.
    """
    _version_re = re.compile(r'__version__\s+=\s+(.*)')
    _url_re = re.compile(r'__url__\s+=\s+(.*)')
    _license_re = re.compile(r'__license__\s+=\s+(.*)')

    with open('yoke/__init__.py', 'rb') as ffinit:
        initcontent = ffinit.read()
        version = str(ast.literal_eval(_version_re.search(
            initcontent.decode('utf-8')).group(1)))
        url = str(ast.literal_eval(_url_re.search(
            initcontent.decode('utf-8')).group(1)))
        license = str(ast.literal_eval(_license_re.search(
            initcontent.decode('utf-8')).group(1)))
    return {
        'version': version,
        'license': license,
        'url': url,
    }


meta = package_meta()


setup(
    name='yoke',
    description='AWS Lambda + API Gateway Deployer',
    keywords='aws lambda apigateway',
    version=meta['version'],
    packages=find_packages(exclude=['tests', 'examples']),
    test_suite='tests',
    install_requires=INSTALL_REQUIRES,
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
    ],
    license=license,
    author="Rackers",
    maintainer_email="ryan.walker@rackspace.com",
    url=meta['url'],
    entry_points={
        'console_scripts': [
            'yoke=yoke.shell:main'
        ]
    },
)
