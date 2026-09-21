#!/usr/bin/env bash
# Manual equivalent of the "deploy" job's SSH script in
# .github/workflows/ci-deploy.yml -- run this directly on the server when
# GitHub Actions isn't available (e.g. Actions usage/minutes exhausted).
# Mirrors that script step-for-step; keep the two in sync if the workflow
# changes.
#
# Usage (on the server, from anywhere -- it cd's to the repo root itself):
#   bash deploy/manual_deploy.sh
#   SKIP_COUNTDOWN=true bash deploy/manual_deploy.sh   # skip the 10-min visitor warning
#
# Unlike the workflow, this does NOT run tests/lint first -- make sure
# main is actually green (CI, or a local test run) before running this.

set -e  # abort on the first failing command, same as script_stop: true in the workflow

cd "$(dirname "$0")/.."   # repo root, regardless of where this script is invoked from
source venv/bin/activate

# Warn visitors before restarting -- announce_deploy runs against whatever
# code is *currently* deployed (the git reset below hasn't happened yet),
# so it's the still-live gunicorn workers that actually render the banner
# for the full window. Skippable via SKIP_COUNTDOWN=true.
if [ "$SKIP_COUNTDOWN" != "true" ]; then
    cd ifiplatform
    if python manage.py announce_deploy --minutes 10; then
        cd ..
        echo "Waiting 10 minutes for the visitor warning to run its course (SKIP_COUNTDOWN=true to skip)..."
        sleep 600
    else
        echo "announce_deploy unavailable on the currently-deployed code -- skipping the warning countdown for this run."
        cd ..
    fi
fi

OLD_SHA=$(git rev-parse HEAD)
git fetch origin main
git reset --hard origin/main

# Keeps /etc/systemd/system/ in sync with whatever's checked into
# deploy/systemd/ -- idempotent, safe to run every time.
sudo cp deploy/systemd/*.service deploy/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sync-peoply-events.timer

source venv/bin/activate
pip install -r requirements.txt
cd ifiplatform
python manage.py migrate
python manage.py collectstatic --noinput --clear

# Only re-syncs (and rewrites DEEPL_GLOSSARY_ID in .env) when
# glossary_terms.py actually changed in this pull -- avoids burning a
# DeepL API call (glossaries are immutable, so this is always a
# delete+recreate) when nothing about it changed. A failure here warns
# and leaves the previous DEEPL_GLOSSARY_ID in place instead of aborting.
if ! git diff --quiet "$OLD_SHA" HEAD -- apps/ifi_home_app/translation/glossary_terms.py; then
    if python manage.py sync_deepl_glossary --write-env; then
        echo "Glossary re-synced and DEEPL_GLOSSARY_ID updated in .env."
    else
        echo "sync_deepl_glossary failed -- leaving the existing DEEPL_GLOSSARY_ID in .env. Machine translation may be using a stale/deleted glossary until this is fixed manually."
    fi
fi

sudo systemctl restart gunicorn

# After the restart (not before) so nothing repopulates it with a value
# computed under the old code -- see clear_cache's own docstring for the
# site-root-paths staleness bug this guards against.
python manage.py clear_cache

# Clears the banner immediately rather than waiting for its own timeout.
python manage.py announce_deploy --clear

echo "Manual deploy complete."
