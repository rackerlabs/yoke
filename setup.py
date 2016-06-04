from setuptools import setup, find_packages

setup(
    name='yoke',
    description='AWS Lambda + API Gateway Deployer',
    keywords='aws lambda apigateway',
    version='0.0.1',
    packages=find_packages(exclude=['tests']),
    test_suite='tests',
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
