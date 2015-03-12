create table proccer_state(
    id integer primary key,
    name varchar not null unique
);
insert into proccer_state (id, name)
    values
    (1, 'ok'),
    (2, 'error'),
    (3, 'late');

create table proccer_job(
    id serial primary key,
    host varchar not null,
    login varchar not null,
    name varchar not null,
    -- when did we last hear from this job, and what was the result
    last_seen timestamp not null,
    -- what is the current status of this job, and when did we change it
    last_stamp timestamp not null,
    state integer not null references proccer_state,
    -- how long should we wait from last_stamp before considering this job
    -- late
    warn_after interval,
    -- optional list of where to mail state-change notifications
    notify varchar -- really json.
);
-- host/login/name uniquely identifies a job.
create unique index proccer_job_id
    on proccer_job(host, login, name);

create table proccer_result(
    id bigserial primary key,
    stamp timestamp not null,
    job integer not null references proccer_job,
    clock_ms integer not null, -- i.e. wall-clock
    output text not null,
    result varchar not null, -- really json
    rusage varchar not null -- really json
);
create index proccer_result_job_stamp
    on proccer_result(job, stamp);

create table proccer_history(
    job integer not null references proccer_job,
    state integer not null references proccer_state,
    started timestamp not null,
    ended timestamp
);
-- there can be only one "current" state per cronjob
create unique index proccer_history_curr
    on proccer_history(job) where ended is null;
