-- Create the Prefect backend database and the Metabase app database
-- (share the Postgres server). Runs only on first container init,
-- connected to POSTGRES_DB as the postgres superuser.
-- NOTE: the prefect password below must match PREFECT_DB_PASSWORD in .env.example / .env.
CREATE ROLE prefect LOGIN PASSWORD 'prefect';
CREATE DATABASE prefect OWNER prefect;
CREATE DATABASE metabase;
