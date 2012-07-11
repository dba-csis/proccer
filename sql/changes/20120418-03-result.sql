alter table proccer_result
    alter column result type varchar;

update proccer_result
    set result = '{}';

alter table proccer_result
    alter column rusage type varchar;

update proccer_result
    set rusage = '{}';
