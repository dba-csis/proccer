from __future__ import with_statement

from commands import getoutput
from contextlib import closing
from email.mime.text import MIMEText
from email.utils import make_msgid
from genshi.template import NewTextTemplate as TextTemplate
import logging
import os
import smtplib
from socket import gethostname

log = logging.getLogger(__name__)

# 64K should be enough for anyone.
MAX_OUTPUT_SIZE = 64 * 1024

default_recipient = os.environ.get('PROCCER_DEFAULT_NOTIFY')
mail_from = os.environ.get('PROCCER_MAIL_FROM', 'proccer@localhost')
mail_reply_to = os.environ.get('PROCCER_REPLY_TO')
smtp_host = os.environ.get('SMTP_HOST', 'localhost')


def state_change_notification(job, result):
    msg, rcpt = mail_for_state(job, job.state, result)
    if msg:
        send_mail(msg, rcpt)


def repeat_notification(job):
    msg, rcpt = mail_for_state(job, 'still ' + job.state, None)
    if msg:
        send_mail(msg, rcpt)


def mail_for_state(job, state, result):
    if not (job.notify or default_recipient):
        log.debug('nobody to notify for job %r state-change', job.id)
        return None, None
    rcpt = job.notify or [default_recipient]

    tag = '[%s]' % unicode(job).replace(' ', '')
    subject = '%s %s' % (tag, state)

    values = {
        'url': os.environ.get('PROCCER_WEB_URL', '').strip('/'),
        'getoutput': getoutput,
        'job': job,
        'state': state,
    }
    if result:
        values['output'] = result['output']
        values['config'] = result['config']

        values['output_truncated'] = len(values['output']) > MAX_OUTPUT_SIZE
        if values['output_truncated']:
            values['output'] = values['output'][:MAX_OUTPUT_SIZE]

    body = body_template.generate(**values).render('text')

    msg = MIMEText(body)
    msg['Message-ID'] = make_msgid(gethostname())
    msg['Subject'] = subject
    msg['From'] = mail_from
    if mail_reply_to:
        msg['Reply-To'] = mail_reply_to
    msg['To'] = ', '.join(rcpt)

    return msg, rcpt


def send_mail(msg, rcpt):
    env_rcpt = rcpt
    env_from = 'proccer@' + gethostname()
    with closing(smtplib.SMTP(smtp_host)) as smtp:
        smtp.sendmail(env_from, env_rcpt, msg.as_string())

body_template = TextTemplate('''\
{% if state == 'ok' %}${getoutput('cowsay "Job okay."')}{% end %}\
{% if state == 'error' %}${getoutput('cowsay -e OO "JOB FAILED!"')}{% end %}\
{% if state not in ['ok', 'error'] %}\
${getoutput('cowsay -e Oo "Job %s"' % state)}\
{% end %}

Job:       ${job}
{% if url %}
URL:       ${url}/job/${job.id}/
{% end %}\
Last seen: ${job.last_seen}
{% if defined('config') %}\
Command:   ${config.get('command', '??')}
{% end %}\
{% if defined('output') %}\
Output:
${'\\n'.join('  ' + line for line in output.split('\\n'))}
{% if output_truncated %}\
Output truncated.
{% end %}\
{% end %}\
''')
