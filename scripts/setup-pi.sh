#!/usr/bin/env bash
# setup-pi.sh — one-time provisioning of a fresh Raspberry Pi 5 for Bedrock 2.0.
# Pushes the local SSH key, installs apt deps, clones the repo, builds venv,
# enables I2C and switches to X11 (Kivy/SDL2 needs Xorg, Bookworm defaults to Wayland).
# Run from the repo root on Windows Git Bash:
#   scripts/setup-pi.sh 192.168.1.55
# Optional env overrides:
#   PI_USER (default pi) PI_PASS (default pipi) SSH_KEY (default ~/.ssh/id_kidpager)
#   REPO_PATH (default ~/bedrock_3_0) BRANCH (default recovery-from-0.8.2)
#   GIT_REMOTE (default https://github.com/Standaoerby/Bedrock_2.0.git)
set -euo pipefail

IP="${1:?Usage: setup-pi.sh <IP_ADDRESS>}"
PI_USER="${PI_USER:-pi}"
PI_PASS="${PI_PASS:-pipi}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_kidpager}"
REPO_PATH="${REPO_PATH:-/home/$PI_USER/bedrock_3_0}"
BRANCH="${BRANCH:-recovery-from-0.8.2}"
GIT_REMOTE="${GIT_REMOTE:-https://github.com/Standaoerby/Bedrock_2.0.git}"

[[ -f "$SSH_KEY.pub" ]] || { echo "❌ No public key at $SSH_KEY.pub"; exit 1; }
command -v plink >/dev/null || { echo "❌ plink (PuTTY) not in PATH"; exit 1; }

PUB=$(cat "$SSH_KEY.pub")

echo "═══ 1/6  PROVISION SSH KEY  ═══"
# `-batch` skips fingerprint prompts; if first connect fails, run once interactively
# without -batch to accept the host key, then re-run setup-pi.sh.
plink -ssh -pw "$PI_PASS" -batch "$PI_USER@$IP" "
  mkdir -p ~/.ssh && chmod 700 ~/.ssh
  touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
  grep -qxF '$PUB' ~/.ssh/authorized_keys || echo '$PUB' >> ~/.ssh/authorized_keys
  echo 'key installed'
"

# From here on, key auth — no more password
SSH=(ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o BatchMode=yes "$PI_USER@$IP")

echo "═══ 2/6  APT DEPS  ═══"
"${SSH[@]}" "sudo apt-get update -qq && sudo apt-get install -y -qq \
    python3 python3-venv python3-pip git \
    python3-lgpio python3-blinka i2c-tools python3-smbus \
    libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    libgstreamer1.0-0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    xdotool unclutter"

echo "═══ 3/6  ENABLE I2C + SWITCH TO X11  ═══"
"${SSH[@]}" "
  # Enable I2C non-interactively (0 = enable in raspi-config nonint)
  sudo raspi-config nonint do_i2c 0 || true
  # Switch desktop to X11 (B1 = console autologin, B4 = desktop autologin
  # with X11 isn't a single nonint code; do_wayland W1=labwc, W2=Wayfire,
  # so we drop to legacy via direct config edit).
  if command -v raspi-config >/dev/null && raspi-config nonint help 2>&1 | grep -q do_wayland; then
    sudo raspi-config nonint do_wayland W3 2>/dev/null || true   # W3 = X (Xorg) on recent raspi-config
  fi
  echo 'I2C and X11 settings applied (a reboot may be needed).'
"

echo "═══ 4/6  CLONE REPO  ═══"
"${SSH[@]}" "
  if [ -d '$REPO_PATH/.git' ]; then
    echo 'repo exists, fetching'
    cd '$REPO_PATH' && git fetch --all --prune
  else
    git clone '$GIT_REMOTE' '$REPO_PATH'
  fi
  cd '$REPO_PATH' && git checkout '$BRANCH' && git pull --ff-only origin '$BRANCH' || git pull --ff-only
"

echo "═══ 5/6  BUILD VENV + INSTALL  ═══"
"${SSH[@]}" "
  cd '$REPO_PATH'
  if [ ! -d venv ]; then
    python3 -m venv venv
  fi
  venv/bin/pip install --upgrade pip wheel
  venv/bin/pip install -r requirements.txt
  echo 'venv ready'
"

echo "═══ 6/6  INSTALL SYSTEMD UNIT (user)  ═══"
"${SSH[@]}" "mkdir -p ~/.config/systemd/user"
scp -i "$SSH_KEY" -o BatchMode=yes scripts/bedrock.service \
    "$PI_USER@$IP:~/.config/systemd/user/bedrock.service"
"${SSH[@]}" "
  # Substitute REPO_PATH placeholder in unit file
  sed -i 's|@REPO_PATH@|$REPO_PATH|g' ~/.config/systemd/user/bedrock.service
  loginctl enable-linger $PI_USER >/dev/null 2>&1 || sudo loginctl enable-linger $PI_USER
  systemctl --user daemon-reload
  systemctl --user enable bedrock.service
  echo 'Unit installed (not started — reboot first if I2C/X11 changed).'
"

# Persist deploy target so future deploy.sh runs don't need an arg
mkdir -p scripts
{
  echo "PI_IP=$IP"
  echo "PI_USER=$PI_USER"
  echo "REPO_PATH=$REPO_PATH"
  echo "BRANCH=$BRANCH"
  echo "SSH_KEY=$SSH_KEY"
} > scripts/.deploy_target

echo ""
echo "✅ Setup done."
echo "   Pi:        $PI_USER@$IP"
echo "   Repo:      $REPO_PATH"
echo "   Branch:    $BRANCH"
echo ""
echo "If I2C or display mode changed, REBOOT the Pi:"
echo "   ssh -i $SSH_KEY $PI_USER@$IP sudo reboot"
echo ""
echo "Then start the service:"
echo "   ssh -i $SSH_KEY $PI_USER@$IP systemctl --user start bedrock"
echo ""
echo "Or run scripts/deploy.sh whenever you want to push new commits."
