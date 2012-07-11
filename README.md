proccer
~~~~~~~

Proccer is a helper for running background-jobs via cron:

 * It keeps your inbox clean, but will notify you about important events (a
   job has begun failing, or has not checked in as expected.)

 * It stores job-results with output, so you can go back and read the debug
   output of recent jobs.

 * It can integrate with Nagios and other monitoring systems.

 * It can handle lockfiles for your jobs.

Installation
============

Installation from a github source checkout:

    python setup.py install

This should install a `proccer` script into your `PATH`, try it out on the
included configuration:

    proccer t

This should leave a log-file `proccer.log` with details of the job run.
