#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='proccer',
    version='0.7.27',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    # These requirements are for the agent. To install the manager's
    # requirements also do `pip install -r manager-requirements.txt`
    # Note: We force lockfile to version 0.8, since that version is known to
    # work (0.9.1 is broken wrt. timeout=0 during acquire).
    install_requires='''
        PyYAML
        jsonlib
        lockfile == 0.8
        requests
    ''',
    entry_points='''
        [console_scripts]
        proccer = proccer.console_scripts:run_processes
    ''',
)
