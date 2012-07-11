#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='proccer',
    version='0.7.7',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=True,
    install_requires=filter(None, [
        line.split('#')[0].strip()
        for line in open('requirements.txt')
    ]),
    entry_points='''
        [console_scripts]
        proccer = proccer.console_scripts:run_processes
    ''',
)
