#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='proccer',
    version='0.7.8',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=True,
    install_requires='''
        PyYAML==3.09
        SQLAlchemy==0.7.6
        Werkzeug==0.8.1
        Flask==0.8
        Flask-Genshi==0.5.1
        blinker==1.2
        jsonlib==1.3.10
        lockfile==0.8
        mock==0.8.0
        psycopg2==2.4.5
        requests>=0.6.1
        wsgi-lite==0.5a2
        wsgiref==0.1.2
    ''',
    entry_points='''
        [console_scripts]
        proccer = proccer.console_scripts:run_processes
    ''',
)
