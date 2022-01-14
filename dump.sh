#!/bin/bash

# local mariadb
DB_HOST="${DB_HOST:-0.0.0.0}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-my-secret-pw}"
DB_NAME="${DB_NAME:-koji}"
MARIA="mariadb -s -h $DB_HOST -P $DB_PORT -u $DB_USER --password=$DB_PASSWORD -D $DB_NAME"

# remote postgresql
PSQL_CONNECTION="${ORIG_DB_CONNECTION:-postgresql://koji-db.example.org:5433/public?sslmode=require}"
PSQL="psql -U anonymous -t -A --field-separator=, -o $CSVFILE $PSQL_CONNECTION"

# how many last tasks/builds has to be refreshed
BACKTRACK="${BACKTRACK:-10000}"

# temporary file with output
CSVFILE="/tmp/psql-dump.csv"

MAXID=`echo "SELECT MAX(id) - $BACKTRACK FROM task;" | $MARIA`
echo "DELETE FROM task WHERE id > $MAXID" | $MARIA

# task
echo "SELECT id, state, create_time, start_time, completion_time, channel_id, host_id, parent, owner, \"method\", arch FROM brew.task WHERE id > $MAXID;" | $PSQL
echo -n "task:    "
wc -l $CSVFILE
echo "LOAD DATA LOCAL INFILE '$CSVFILE' INTO TABLE task FIELDS TERMINATED BY ',';" | $MARIA
rm $CSVFILE
#exit

# build
MAXID=`echo "SELECT MAX(id) - $BACKTRACK FROM build;" | $MARIA`
echo "DELETE FROM build WHERE id > $MAXID" | $MARIA
#MAXID=`echo "SELECT MAX(id) FROM build;" | $MARIA`
echo "SELECT id, pkg_id, start_time, completion_time, state, task_id, owner FROM brew.build WHERE id > $MAXID;" | $PSQL
echo -n "build:   "
wc -l $CSVFILE
echo "LOAD DATA LOCAL INFILE '$CSVFILE' INTO TABLE build FIELDS TERMINATED BY ',';" | $MARIA
rm $CSVFILE

# users
MAXID=`echo "SELECT MAX(id) FROM users;" | $MARIA`
#MAXID=0
echo "SELECT id, name FROM brew.users WHERE id > $MAXID;" | $PSQL
echo -n "users:   "
wc -l $CSVFILE
echo "LOAD DATA LOCAL INFILE '$CSVFILE' INTO TABLE users FIELDS TERMINATED BY ',';" | $MARIA
rm $CSVFILE

# packages
MAXID=`echo "SELECT MAX(id) FROM package;" | $MARIA`
echo "SELECT id, name FROM brew.package WHERE id > $MAXID;" | $PSQL
echo -n "package: "
wc -l $CSVFILE
echo "LOAD DATA LOCAL INFILE '$CSVFILE' INTO TABLE package FIELDS TERMINATED BY ',';" | $MARIA
rm $CSVFILE
