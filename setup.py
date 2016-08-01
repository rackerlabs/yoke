from setuptools import setup, find_packages

setup(
    name='yoke',
    description='AWS Lambda + API Gateway Deployer',
    keywords='aws lambda apigateway',
    version='0.0.1',
    packages=find_packages(exclude=['tests']),
    test_suite='tests',
    install_requires=[
        'boto3==1.3.0',
        'botocore>=1.4.24',
        'docutils==0.12',
        'futures==3.0.5',
        'Jinja2==2.8',
        'jmespath==0.9.0',
        'jsonref==0.1',
        'lambda-uploader==1.0.0',
        'MarkupSafe==0.23',
        'python-dateutil==2.5.3',
        'PyYAML==3.11',
        'retrying==1.3.3',
        'ruamel.ordereddict==0.4.9',
        'ruamel.yaml==0.11.11',
        'six==1.10.0',
        'virtualenv==15.0.2',
        'yoke==0.0.1',
    ],
    classifiers=[
        "Programming Language :: Python :: 2.7"
    ],
    author="Rackers",
    entry_points={
        'console_scripts': [
            'yoke=yoke.shell:main'
        ]
    },
)
