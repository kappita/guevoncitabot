#!/bin/sh
set -e

# yt-dlp rewrites the cookie jar on exit, so copy the read-only mount into a
# writable location owned by this user (botuser) before starting.
if [ -f /cookies/cookies.txt ]; then
    rm -f /data/cookies.txt
    cp /cookies/cookies.txt /data/cookies.txt
fi

exec "$@"
