#!/usr/bin/env bash
set -euo pipefail

RACE_BACKSTOP_SEC=2
timeout_sec="$1"
runtime_dir="/run/user/$(id -u)"
deadline=$((SECONDS + timeout_sec))

until compgen -G "$runtime_dir/sway-ipc.*.sock" >/dev/null; do
  ((SECONDS < deadline)) || { echo "vekrona-dev: no sway session after ${timeout_sec}s" >&2; exit 1; }
  watch_dir="$runtime_dir"
  [[ -d "$watch_dir" ]] || watch_dir=/run/user
  status=0
  inotifywait -qq -t "$RACE_BACKSTOP_SEC" -e create "$watch_dir" || status=$?
  ((status != 1)) || { echo "vekrona-dev: inotifywait failed on $watch_dir" >&2; exit 1; }
done
