# shellcheck shell=bash
XDG_RUNTIME_DIR="/run/user/$(id -u)"
sway_sockets=("$XDG_RUNTIME_DIR"/sway-ipc.*.sock)
[[ ${#sway_sockets[@]} -eq 1 && -S "${sway_sockets[0]}" ]] || {
  echo "vekrona-dev: expected one sway session socket, found: ${sway_sockets[*]}" >&2
  exit 1
}
export XDG_RUNTIME_DIR SWAYSOCK="${sway_sockets[0]}" WAYLAND_DISPLAY=wayland-1
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
