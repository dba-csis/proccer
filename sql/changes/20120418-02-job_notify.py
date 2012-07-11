import jsonlib as json

cnx.execute('''
    alter table proccer_job
        alter column notify type varchar
''')

jobs = cnx.execute('select id, notify from proccer_job')
for job_id, notify in jobs:
    if notify is None:
        continue
    cnx.execute('update proccer_job set notify = %s where id = %s',
                [json.dumps(notify[1:-1].split(',')), job_id])
