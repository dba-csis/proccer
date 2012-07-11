\set QUIET on
\set ON_ERROR_STOP

SET client_encoding = 'UTF-8';
SET check_function_bodies = true;
SET client_min_messages = warning;

drop table if exists proccer_job cascade;
drop table if exists proccer_state cascade;
drop table if exists proccer_result cascade;
drop table if exists proccer_history cascade;

\i current.sql
