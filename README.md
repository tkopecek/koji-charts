# Koji Charts
Simple statistics server for https://pagure.io/koji

It mirrors basic information about tasks and builds from koji in local db. The
reason is simple - to not cause unnecessary load on production server. It can be
changed (not sure how many mariadb-specific SQL is now in) to use the production
db instead but it is not recommended. Maria is used for some faster aggregation
functions like COUNT, but it probably should be changed back to PostgreSQL in
future as it would be more compatible with prod instance.

Application itself is tailored to be run in openshift but run locally without
any problems.

In rough state now. You'll need to perform following steps:

 - Run mariadb container via `db.sh`. `DB_DIR` is needed to be defined for
   permanent db storage.
 - Init db manually with `schema.sql`. (Subset of koji's `schema.sql`)
 - Run `dump.sh` which will populate the mariadb. Note, that it can be overkill
 for some production deployments and these big dumps can timeout. In such case,
 running it in batches would help.
 - Set up `cron` with running this update periodically. Running it after initial
 pre-population should be almost for free, so running it e.g. each hour is ok.

 - Local run
    - create virtualenv and populate it with `requirements.txt`
    - Run `www/run.sh` or just directly `flask run` with approppriate variables
 - Container
    - build container via `podman build -t koji-charts`
    - run it `podman run --name koji-charts -p 5000:5000 koji-charts:latest`
    - visit `http://localhost:5000`
