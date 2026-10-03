# vekrona-dev

The sandbox where vekrona changes are verified. Never verify a vekrona change on the host
desktop, and never install test dependencies there: do it in this VM.

## Feedback loop for a vekrona change

1. `bin/vekrona-dev up` (once), then `bin/vekrona-dev install` after every edit in the vekrona
   checkout (`VEKRONA_REPO`, default `~/wrk/vekrona`). install.sh reloads a running sway.
2. `bin/vekrona-dev session` to get a logged-in sway session.
3. Reproduce with real input (`key`, `hold`, `type`, `click`) and look with `shot` (then Read
   the PNG) and `see ocr|luma|text|diff`. `sh CMD` runs CMD inside the session (SWAYSOCK set).
4. Write the behavior down as a scenario in vekrona's `tests/e2e/` and run it with
   `bin/vekrona-dev e2e`. Prove it catches the bug: it must fail after
   `bin/vekrona-dev install --rev <commit before the fix>` and pass after `bin/vekrona-dev install`.
5. `bin/vekrona-dev test` runs vekrona's own suites in the guest.

## Rules

- Same conventions as vekrona: `set -euo pipefail`, fail early, no dead code, no comments
  except vendor quirks.
- Never pace with `sleep`. Wait on guest events; for the screen use `until`, which retries
  back to back up to a deadline.
- Self-tests (`bin/vekrona-dev self-test`) run in the guest, through the public CLIs.
- Do not edit `bin/vekrona-dev` while a long command from it is running: bash reads the script
  as it goes.
