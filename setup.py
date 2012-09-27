#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='proccer',
    version='0.7.10',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    # These requirements are for the agent. To install the manager's
    # requirements also do `pip install -r manager-requirements.txt`
    install_requires='''
        PyYAML
        jsonlib
        lockfile
        psycopg2
        requests
    ''',
    entry_points='''
        [console_scripts]
        proccer = proccer.console_scripts:run_processes
    ''',
)
