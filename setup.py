#!/usr/bin/env python
# coding: utf-8

from setuptools import setup, find_packages

version = {}

with open("lambda_harness/_version.py") as fp:
    exec(fp.read(), version)

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='lambda-harness',
    version=version['__version__'],
    packages=find_packages(exclude=('docs')),
    install_requires=requirements,
    provides=[ 'lambda_harness' ],
    author='Brandon Davidson',
    description='Basic test harness for AWS Lambda',
    long_description=readme,
    license=license,
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
    entry_points={
        'console_scripts': [
            'invoke-lambda=lambda_harness.cli:invoke',
            'lambda=lambda_harness.cli:cli'
        ]
    },

)

