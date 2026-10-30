#!/usr/bin/env bash
# Build the site and deploy it to the Aalto vhost (machinelearning.aalto.fi)
# straight from this machine. This is the manual path, for when you want a
# change live immediately; routine syncing is automatic via the site-build
# branch (see .github/workflows/publish-site-build.yml) which a cron job on
# webfiles pulls every 10 minutes.
#
# The webroot lives on webfiles.aalto.fi (/l/data/<vhost>), reachable only via
# the kosh jump host. Both hops use key auth via the "webfiles" alias in
# ~/.ssh/config, which sets ProxyJump plus connection multiplexing — no
# password, no manual tunnel. Aalto home is shared NFS, so the single
# ~/.ssh/authorized_keys there covers kosh and webfiles alike.
#
# Usage: scripts/deploy_vhost.sh
set -euo pipefail

REMOTE="${REMOTE:-webfiles}"
WEBROOT="${WEBROOT:-/l/data/machinelearning.aalto.fi}"
SITE="$(cd "$(dirname "$0")/.." && pwd)/_site"

echo "==> Building site"
bundle exec jekyll build --destination "$SITE"

echo "==> Deploying to $REMOTE:$WEBROOT"
# No -p: let the remote umask (002) set permissions. --delete keeps the webroot
# in sync with the build, so pages removed from the repo leave the live site.
rsync -rltvz --delete "$SITE"/ "$REMOTE:$WEBROOT/"

echo "==> Verifying"
for path in / /people/ /research/ /teaching/ /meetups/ /assets/css/style.css; do
  curl -sS -o /dev/null -w "%{http_code}  https://machinelearning.aalto.fi$path\n" \
    -m 20 "https://machinelearning.aalto.fi$path"
done
