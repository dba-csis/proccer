alter table proccer_result
    add column state integer references proccer_state;

update proccer_result
    set state = 1;

alter table proccer_result
    alter column state set not null;
