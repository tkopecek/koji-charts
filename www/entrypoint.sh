#!/bin/sh
source /opt/venv/bin/activate
cd /opt/www
export FLASK_APP=app.py FLASK_DEBUG=0 FLASK_ENV=production
flask run -h 0.0.0.0
