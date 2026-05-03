# Deploy scripts

Two-step deploy targeting fresh Raspberry Pi 5 with Pi OS Bookworm.

```
scripts/
├── setup-pi.sh        # one-time provisioning
├── deploy.sh          # repeatable updates
├── bedrock.service    # systemd user unit (template)
└── README.md          # this file
```

After `setup-pi.sh` runs once, deploys are just `scripts/deploy.sh` from
the repo root — IP/branch/path are remembered in `scripts/.deploy_target`
(gitignored).

## Prerequisites (on Windows dev box)

- Git Bash (already in use)
- PuTTY's `plink` in PATH (`/c/Program Files/PuTTY/`) — used once to push
  the SSH key, then everything is key-based
- An ed25519 keypair at `~/.ssh/id_kidpager` (override with `SSH_KEY=...`)

## Quick start (fresh Pi)

```bash
# Find the Pi's IP first
#   nmap -sn 192.168.1.0/24    # or check your router DHCP table
#   default credentials: pi / pipi

cd /c/_PROJECTS/Bedrock_2.0
scripts/setup-pi.sh 192.168.1.55       # replace with actual IP
ssh -i ~/.ssh/id_kidpager pi@192.168.1.55 sudo reboot   # if I2C/X11 changed
ssh -i ~/.ssh/id_kidpager pi@192.168.1.55 systemctl --user start bedrock
```

`setup-pi.sh` does:

1. Pushes your public key into `~/.ssh/authorized_keys` (using `plink` with
   the `pi/pipi` default password). After this, no more password prompts.
2. `apt-get install` Python3, venv, lgpio, blinka, SDL2 dev libs, gstreamer.
3. `raspi-config nonint do_i2c 0` to enable I2C, and tries to switch the
   desktop to X11 (Bookworm defaults to Wayland which Kivy/SDL2 can't drive).
4. `git clone` the repo to `~/bedrock_3_0` and checkout the recovery branch.
5. Builds `venv` and installs `requirements.txt`.
6. Drops `bedrock.service` into `~/.config/systemd/user/`, substitutes the
   `@REPO_PATH@` placeholder, enables `loginctl enable-linger` so the unit
   stays running after logout, and `enable`s the service (does NOT start it
   — first manually verify nothing else needs a reboot).

## Repeat deploy

```bash
git commit -m "..."          # commit your changes locally
scripts/deploy.sh            # uses saved target from .deploy_target
# or override the target one-off:
scripts/deploy.sh 192.168.1.99
```

`deploy.sh` does:

1. `git push origin <branch>` from the dev box.
2. Pre-flight on the Pi: SSH liveness, free disk, `dmesg | grep mmc` for
   recent SD-card I/O errors (asks for confirmation if any), `git fsck`.
3. `tar -czf` backup of `config/` into `_backups/state-<ts>.tgz`, keeps
   only the last 10.
4. Records the previous git HEAD (rollback target).
5. `git fetch && git reset --hard origin/<branch>` on Pi.
6. If `requirements.txt` changed in the diff, `pip install -r requirements.txt`.
7. Smoke test: `venv/bin/python -c 'import main'`. Failure → rollback to the
   previous HEAD and exit non-zero.
8. `systemctl --user restart bedrock` and prints status.

## Env overrides

Set before any script:

| var | default | meaning |
|---|---|---|
| `PI_IP` | from `.deploy_target` | Pi IPv4 |
| `PI_USER` | `pi` | SSH user |
| `PI_PASS` | `pipi` | only used by `setup-pi.sh` once |
| `SSH_KEY` | `~/.ssh/id_kidpager` | private key path |
| `REPO_PATH` | `/home/$PI_USER/bedrock_3_0` | clone target on Pi |
| `BRANCH` | `recovery-from-0.8.2` | branch to deploy |
| `GIT_REMOTE` | GitHub URL | initial clone source |

## Notes about SD card degradation

The Pi's SD card has shown signs of failing. `deploy.sh` does three things
to be defensive:

- Checks `dmesg` for `mmc.*(error|fail|recover|timeout)` and `EXT4-fs error`
  messages and asks before continuing.
- Runs `git fsck` to surface objects damaged by bad sectors before any
  destructive operation.
- Saves `config/` snapshots (last 10) to `_backups/`.

If `git fsck` reports missing objects on the Pi, the simplest recovery is
to wipe `~/bedrock_3_0` and re-run `setup-pi.sh` — fresh clone repopulates
all objects.

For a longer-term fix, consider:

- Move the repo and venv to USB SSD (`/mnt/ssd/bedrock_3_0`) — Pi5 boots
  fine off USB.
- Mount `~/bedrock_3_0` with `noatime` to reduce SD writes.
- Send logs to memory / journald with `Storage=volatile` to avoid SD wear.

## Troubleshooting

**`plink: Could not establish a connection`** — Pi not on the network or
firewall blocks port 22. Check `nmap -sn` and try ping.

**First connect prompts for fingerprint, plink batch mode rejects it** —
run plink interactively once to accept:
```
plink -ssh pi@<IP>
```
Type `y` at the prompt, exit, re-run setup.

**Smoke test fails on Pi but works locally** — likely a dep that exists on
Windows venv but not on Pi. Check the traceback:
```
ssh -i ~/.ssh/id_kidpager pi@<IP> "cd ~/bedrock_3_0 && venv/bin/python main.py"
```

**`bedrock.service` fails with display errors** — Pi still on Wayland.
Run `sudo raspi-config` → Advanced Options → Wayland → X11.
