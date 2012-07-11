from __future__ import with_statement

from datetime import datetime
from flask import Flask, json, jsonify, request, flash, url_for, redirect
from flask.ext.genshi import Genshi, render_response
import imp
import logging
import os
from werkzeug.exceptions import BadRequest

from proccer.database import session_manager, Job
from proccer.database import update_proccer_job, add_proccer_result
from proccer.signals import report_received

log = logging.getLogger('proccer.app')

# We do not want our configuration to be garbage-collected, since it can
# contain arbitrary code, like signal handlers, so we cannot use from_envvar.
def from_envvar(config, name):
    filename = os.environ.get(name)
    if not filename:
        return None

    d = imp.new_module('config')
    d.__file__ = filename
    try:
        execfile(filename, d.__dict__)
    except IOError:
        return None
    config.from_object(d)
    return d

app = Flask(__name__)
app.config.from_object('proccer.default_settings')
local_config = from_envvar(app.config, 'PROCCER_SETTINGS')

genshi = Genshi(app)

@app.route('/')
def index():
    with session_manager() as session:
        jobs = (session
                    .query(Job)
                    .filter(Job.deleted == None)
                    .order_by(Job.login, Job.host, Job.name))

        text = Job.login + ' ' + Job.host + ' ' + Job.name
        for q in request.args.get('q', '').strip().split():
            jobs = jobs.filter(text.contains(q))

        return render_response('index.html', {'jobs': jobs.all()})

@app.route('/job/<job_id>/')
def job(job_id):
    with session_manager() as session:
        job = Job.get(session, job_id)
        return render_response('job.html', {
            'job': job,
            'results': job.results.limit(7).all(),
        })

@app.route('/job/<job_id>/delete', methods=['POST'])
def delete_job(job_id):
    with session_manager() as session:
        job = Job.get(session, job_id)
        job.deleted = datetime.utcnow()
        flash('Job deleted')
    return redirect(url_for('index'))

@app.route('/api/1.0/report', methods=['POST'])
def report():
    try:
        result = json.loads(request.data, use_decimal=False)
    except Exception, e:
        raise BadRequest()

    report_received.send(result)
    return jsonify(ok=True)

@report_received.connect
def to_database(result):
    with session_manager() as session:
        job = update_proccer_job(session, result)
        add_proccer_result(session, job, result)

if __name__ == '__main__':
    app.run(host=app.config['HOST'], port=app.config['PORT'])
