#!/bin/bash
# Pull the built site from GitHub and publish it to the vhost webroot.
#
# Installed on webfiles.aalto.fi (sorvi) and run from cron every 10 minutes.
# The site-build branch is produced by .github/workflows/publish-site-build.yml
# in ml4bigdata/ml4bigdata.github.io. Pulling (rather than letting GitHub push)
# is deliberate: kosh offers publickey auth only to Aalto addresses, so no
# credential for this host can live at GitHub. The repo is public, so this
# needs no credentials at all.
#
# What was last published is tracked in a state file rather than by diffing
# HEAD before and after the fetch, so a fresh clone, a failed rsync, or a
# hand-edited webroot all converge on the next run.
set -euo pipefail

REPO_URL="https://github.com/ml4bigdata/ml4bigdata.github.io.git"
CLONE="$HOME/vhost-site"
WEBROOT="/l/data/machinelearning.aalto.fi"
BRANCH="site-build"
STATE="$HOME/.vhost-published-rev"

log() { echo "$(date -u +%FT%TZ) $*"; }

if [ ! -d "$CLONE/.git" ]; then
    log "cloning $BRANCH"
    git clone --quiet --single-branch -b "$BRANCH" "$REPO_URL" "$CLONE"
fi

cd "$CLONE"
# Explicit refspec: git 1.8.3.1 (this host) does NOT opportunistically update
# refs/remotes/origin/<branch> when fetching a branch by name — that arrived in
# git 1.8.4 — so "git fetch origin site-build" would leave origin/site-build
# stale and the reset below would be a no-op.
git fetch --quiet origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
git reset --quiet --hard "refs/remotes/origin/$BRANCH"

head=$(git rev-parse HEAD)
published=$(cat "$STATE" 2>/dev/null || echo none)

if [ "$head" = "$published" ]; then
    exit 0
fi

log "publishing ${published:0:8} -> ${head:0:8}"
# No -p: the remote umask (002) sets permissions. --exclude protects .git from
# both the copy and --delete. --omit-dir-times because the webroot itself is
# owned by pse_d0, so setting its mtime is not permitted.
rsync -rlt --omit-dir-times --delete --exclude='.git' "$CLONE"/ "$WEBROOT"/
# Only recorded after a successful rsync, so a failure retries next run.
echo "$head" > "$STATE"
log "published ${head:0:8}"
