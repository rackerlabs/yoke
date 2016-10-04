from setuptools import setup, find_packages

setup(
    name='yoke',
    description='AWS Lambda + API Gateway Deployer',
    keywords='aws lambda apigateway',
    version='0.0.1',
    packages=find_packages(exclude=['tests']),
    test_suite='tests',
    install_requires=[
        'boto3==1.4.0',
        'botocore>=1.4.24',
        'Jinja2==2.8',
        'jsonref==0.1',
        'lambda-uploader==1.0.3',
        'retrying==1.3.3',
        'ruamel.yaml==0.11.11',
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
