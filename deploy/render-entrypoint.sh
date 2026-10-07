#!/bin/sh
set -eu

: "${PORT:=10000}"
: "${API_READ_KEY:?API_READ_KEY must be set by Render}"
: "${API_SECRET_KEY:?API_SECRET_KEY must be set by Render}"

export PORT API_READ_KEY
envsubst '${PORT} ${API_READ_KEY}' \
    < /etc/nginx/templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf

exec supervisord -n -c /etc/supervisor/supervisord.conf
