#!/usr/bin/env bash
# Run the bedrock smoke suite.
# - locally on Windows dev box: ./scripts/test.sh
# - remotely on the Pi:         ./scripts/test.sh --pi
#
# Pass extra args to filter test groups: sensors, audio, services, themes.
set -euo pipefail

PI=0
GROUPS=()
for a in "$@"; do
  case "$a" in
    --pi) PI=1 ;;
    *)    GROUPS+=("$a") ;;
  esac
done

if [[ $PI -eq 1 ]]; then
  TARGET_FILE="$(dirname "$0")/.deploy_target"
  [[ -f "$TARGET_FILE" ]] && source "$TARGET_FILE"
  PI_USER="${PI_USER:-pi}"
  SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_kidpager}"
  REPO_PATH="${REPO_PATH:-/home/$PI_USER/bedrock_3_0}"
  SSH=(ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o BatchMode=yes "$PI_USER@${PI_IP:?}")
  echo "Running on $PI_USER@$PI_IP, repo $REPO_PATH"
  "${SSH[@]}" "cd '$REPO_PATH' && KIVY_AUDIO=ffpyplayer SDL_AUDIODRIVER=pulse \
      venv/bin/python -m tests.smoke ${GROUPS[*]}"
else
  cd "$(dirname "$0")/.."
  if [[ -x venv/Scripts/python.exe ]]; then
    PY=venv/Scripts/python.exe
  elif [[ -x venv/bin/python ]]; then
    PY=venv/bin/python
  else
    PY=python
  fi
  exec "$PY" -m tests.smoke "${GROUPS[@]}"
fi
