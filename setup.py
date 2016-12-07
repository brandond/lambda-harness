#!/usr/bin/env python
# coding: utf-8

from setuptools import setup, find_packages
import sys

if sys.version_info <= (2,7) or sys.version_info >= (3,0):
    raise RuntimeError("lambda-harness doesn't support Python versions other than 2.7")

version = {}

with open("lambda_harness/_version.py") as fp:
    exec(fp.read(), version)

with open('README.rst') as f:
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
    author_email='brad@oatmail.org',
    url='https://github.com/brandond/lambda-harness',
    description='Test harness for AWS Lambda',
    long_description=readme,
    license=license,
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
    ],
    entry_points={
        'console_scripts': [
            'invoke-lambda=lambda_harness.cli:invoke',
            'lambda=lambda_harness.cli:cli'
        ]
    },
)
