#!/usr/bin/env bash
# deploy.sh — push the current branch to the Pi and (re)start the service.
# Reads scripts/.deploy_target (created by setup-pi.sh) for IP/USER/REPO_PATH.
# Pre-flight: SSH liveness, free disk, recent SD-card I/O errors, git fsck.
# On smoke-test failure rolls back to the previous HEAD.
set -euo pipefail

# Load saved deploy target
TARGET_FILE="$(dirname "$0")/.deploy_target"
[[ -f "$TARGET_FILE" ]] && source "$TARGET_FILE"

# Allow CLI/env override
PI_IP="${1:-${PI_IP:-}}"
PI_USER="${PI_USER:-pi}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_kidpager}"
REPO_PATH="${REPO_PATH:-/home/$PI_USER/bedrock_3_0}"
BRANCH="${BRANCH:-recovery-from-0.8.2}"

if [[ -z "$PI_IP" ]]; then
  echo "❌ PI_IP not set. Usage: deploy.sh <IP>  or  run setup-pi.sh first."
  exit 1
fi

SSH=(ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o BatchMode=yes "$PI_USER@$PI_IP")

# ────────────────────────────────────────────────────────────────────────
# 0. Push current branch to GitHub so Pi can pull it.
# ────────────────────────────────────────────────────────────────────────
echo "═══ PUSH local '$BRANCH' to origin ═══"
LOCAL_HEAD=$(git rev-parse HEAD)
git push origin "$BRANCH"

# ────────────────────────────────────────────────────────────────────────
# 1. Pre-flight: connectivity, disk space, SD card health, git integrity.
# ────────────────────────────────────────────────────────────────────────
echo ""
echo "═══ PRE-FLIGHT ═══"
"${SSH[@]}" "echo Pi alive: \$(uname -n) — kernel \$(uname -r)"

# Free disk on the partition holding the repo
"${SSH[@]}" "df -h '$REPO_PATH' 2>/dev/null || df -h /home" | tail -1 | \
  awk '{ printf "Disk: %s used (%s free)\n", $5, $4 }'

# Look for recent mmcblk / I/O errors in dmesg (SD card health proxy).
# Don't fail on grep no-match — pipefail would otherwise abort.
ERRORS=$( ("${SSH[@]}" "sudo dmesg --time-format iso 2>/dev/null | \
  grep -iE 'mmc.*(error|fail|recover|timeout)|EXT4-fs error|I/O error' | \
  tail -10" || true) )
if [[ -n "$ERRORS" ]]; then
  echo ""
  echo "⚠️  Recent kernel I/O / mmc messages on Pi (SD card may be degrading):"
  echo "$ERRORS" | sed 's/^/   /'
  echo ""
  read -r -p "Continue with deploy anyway? [y/N] " confirm
  [[ "$confirm" == "y" || "$confirm" == "Y" ]] || { echo "aborted"; exit 1; }
fi

# Quick git fsck on remote — surfaces corrupted objects from bad sectors
echo "→ git fsck"
"${SSH[@]}" "cd '$REPO_PATH' && git fsck --no-progress --no-dangling 2>&1 | tail -5 || \
  echo '⚠️ git fsck reported issues — see above'"

# ────────────────────────────────────────────────────────────────────────
# 2. Backup configs + remember rollback point.
# ────────────────────────────────────────────────────────────────────────
echo ""
echo "═══ BACKUP ═══"
TS=$(date +%Y%m%d-%H%M%S)
"${SSH[@]}" "
  mkdir -p '$REPO_PATH/_backups'
  tar -czf '$REPO_PATH/_backups/state-$TS.tgz' -C '$REPO_PATH' \
      config 2>/dev/null || echo '(no config to back up yet)'
  # Keep only last 10 backups so the SD card doesn't fill
  ls -1t '$REPO_PATH/_backups/' | tail -n +11 | \
      xargs -I {} rm -f '$REPO_PATH/_backups/{}'
"

PREV_HEAD=$("${SSH[@]}" "cd '$REPO_PATH' && git rev-parse HEAD")
echo "Previous Pi HEAD: $PREV_HEAD"

# ────────────────────────────────────────────────────────────────────────
# 3. Fetch + checkout target branch.
# ────────────────────────────────────────────────────────────────────────
echo ""
echo "═══ FETCH + CHECKOUT $BRANCH ═══"
"${SSH[@]}" "
  cd '$REPO_PATH'
  git fetch --all --prune
  git checkout '$BRANCH' 2>&1 | tail -3
  git reset --hard 'origin/$BRANCH'
"

NEW_HEAD=$("${SSH[@]}" "cd '$REPO_PATH' && git rev-parse HEAD")
echo "New Pi HEAD:      $NEW_HEAD"

if [[ "$NEW_HEAD" == "$PREV_HEAD" ]]; then
  echo "(no commits since last deploy)"
fi

# ────────────────────────────────────────────────────────────────────────
# 4. Conditionally re-install Python deps if requirements.txt changed.
# ────────────────────────────────────────────────────────────────────────
if "${SSH[@]}" "cd '$REPO_PATH' && \
   git diff --name-only '$PREV_HEAD' '$NEW_HEAD' 2>/dev/null | grep -q '^requirements\.txt$'"; then
  echo ""
  echo "═══ pip install (requirements.txt changed) ═══"
  "${SSH[@]}" "cd '$REPO_PATH' && venv/bin/pip install -r requirements.txt"
fi

# ────────────────────────────────────────────────────────────────────────
# 4b. Sync systemd unit if scripts/bedrock.service changed.
# ────────────────────────────────────────────────────────────────────────
if "${SSH[@]}" "cd '$REPO_PATH' && \
   git diff --name-only '$PREV_HEAD' '$NEW_HEAD' 2>/dev/null | grep -q '^scripts/bedrock\.service$'"; then
  echo ""
  echo "═══ systemd unit changed — re-installing ═══"
  "${SSH[@]}" "
    sed 's|@REPO_PATH@|$REPO_PATH|g' '$REPO_PATH/scripts/bedrock.service' \
      > ~/.config/systemd/user/bedrock.service
    systemctl --user daemon-reload
  "
fi

# ────────────────────────────────────────────────────────────────────────
# 5. Smoke test — import the entry module. Failure → rollback.
# ────────────────────────────────────────────────────────────────────────
echo ""
echo "═══ SMOKE TEST ═══"
if ! "${SSH[@]}" "cd '$REPO_PATH' && KIVY_NO_ARGS=1 venv/bin/python -c 'import main; print(\"import OK\")'"; then
  echo "❌ Smoke test failed — rolling back to $PREV_HEAD"
  "${SSH[@]}" "cd '$REPO_PATH' && git reset --hard '$PREV_HEAD'"
  exit 1
fi

# ────────────────────────────────────────────────────────────────────────
# 6. Restart service (user-mode systemd unit installed by setup-pi.sh).
# ────────────────────────────────────────────────────────────────────────
echo ""
echo "═══ RESTART ═══"
if "${SSH[@]}" "systemctl --user list-unit-files bedrock.service --no-legend 2>/dev/null | grep -q bedrock"; then
  "${SSH[@]}" "systemctl --user restart bedrock.service"
  sleep 2
  "${SSH[@]}" "systemctl --user status bedrock.service --no-pager -l | head -15"
else
  echo "⚠️  No bedrock.service installed. Run scripts/setup-pi.sh first, or start manually:"
  echo "   ssh -i $SSH_KEY $PI_USER@$PI_IP \"cd '$REPO_PATH' && venv/bin/python main.py\""
fi

echo ""
echo "✅ Deploy complete."
echo "   $PREV_HEAD → $NEW_HEAD"
# On Trixie, user-scope `journalctl --user` is empty by default; user logs land
# in the system journal under _SYSTEMD_USER_UNIT — needs sudo to read.
echo "   logs:  ssh -i $SSH_KEY $PI_USER@$PI_IP \"sudo journalctl _SYSTEMD_USER_UNIT=bedrock.service -f\""
