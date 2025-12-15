#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"          # /home/pi/BangladinoRobot/Backup
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"           # /home/pi/BangladinoRobot
LOCAL_NAME="$(basename "${BASE_DIR}")"               # BangladinoRobot (o nuovo nome se rinomini la cartella)

/home/pi/Backup/common-backup.sh "${LOCAL_NAME}" "${BASE_DIR}" "Home/${LOCAL_NAME}" "${SCRIPT_DIR}"
