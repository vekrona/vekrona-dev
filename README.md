# vekrona-dev

A disposable [Lima](https://lima-vm.io) VM running [vekrona](https://github.com/vekrona/vekrona),
driven by keyboard input and checked on screen. It is where vekrona is tested, so that nothing
under test (and no test dependency) touches the developer's own desktop.

```
vekrona-dev up          # Fedora 44 cloud image under QEMU/KVM, vekrona checkout mounted read-only
vekrona-dev install     # copy the working tree in, run ./install.sh --no-pull --skip 10-nvidia
vekrona-dev session     # log in at the greeter by typing, wait for sway
vekrona-dev hold super-shift-4 1500
vekrona-dev see luma    # 0-255 mean luminance of a fresh screenshot
vekrona-dev see text 'Saved to'
vekrona-dev key esc
vekrona-dev e2e ~/.local/share/vekrona/tests/e2e/*.sh
vekrona-dev test        # vekrona's tests/run.sh, inside the VM
vekrona-dev usb attach 1050:0407   # hand a host YubiKey to the running guest
vekrona-dev usb detach 1050:0407   # take it back
```

`vekrona-dev` with no arguments lists every command.

## How it works

- **VM.** `lima/vekrona.yaml`: Fedora 44 cloud image, `vmType: qemu` (the QMP socket is what
  makes keyboard input and screenshots possible; Lima's `vz` driver on macOS has none), a VNC
  display, no containerd, user `vekrona` / password `vekrona`. A boot-time provision script
  installs the guest tools: tesseract, OpenCV, libinput tools, and vekrona's test dependencies
  (`anaconda-core` and friends).
- **Mounts** (all read-only): the vekrona checkout (`VEKRONA_REPO`) at `/mnt/vekrona`, this repo
  at `/mnt/vekrona-dev`, and the screenshot directory at `/mnt/vekrona-dev-shots`.
- **Install.** `sync` rsyncs the working tree (tracked and untracked, `.gitignore` respected)
  or a committed `--rev` into `~/.local/share/vekrona` in the guest; `install` runs the real
  installer there. The first `session` after an install restarts the VM into the graphical
  target that the installer enabled.
- **Input.** `lib/qmp.py` talks to Lima's `qmp.sock`: `send-key` for chords and typing,
  `send-key` with `hold-time` for held keys (QEMU times the release), `input-send-event` for
  clicks, `screendump` for screenshots.
- **USB.** `usb attach VID:PID` sends QMP `device_add` (`usb-host` on Lima's `usb-bus`, id
  `hostusb-VID-PID`), then waits until the guest's sysfs lists the device; `usb detach` sends
  `device_del` for the same id. QEMU opens the device node itself, so the user needs read/write
  access to it (e.g. `sudo setfacl -m u:$USER:rw /dev/bus/usb/BUS/DEV`). If a host process holds
  an interface through usbfs, attach refuses: for a security key that is `pcscd`, so run
  `sudo systemctl stop pcscd.socket pcscd.service` first. While attached, the device belongs to
  the VM: the host cannot use it, and QEMU takes it back on every replug (it matches VID:PID),
  until `usb detach`. Never attach the user's only security key without detaching it afterwards.
- **Vision.** `guest/vision.py` runs inside the VM (so OpenCV and tesseract never land on the
  host): OCR, mean luminance, mean difference between two screenshots. Deterministic and
  offline; no model judges a screenshot.
- **Waiting.** Guest events where one exists (`inotifywait` on the sway socket, `libinput
  debug-events`, sway IPC subscriptions); for the screen, which has no change event, `until`
  reruns a check back to back up to a deadline.

## Requirements

An x86_64 Linux host with KVM, and Lima 2.x with QEMU (`nix profile add nixpkgs#lima` brings
both; Fedora does not package Lima).

## Tests

`vekrona-dev self-test` runs `tests/` inside the VM.
