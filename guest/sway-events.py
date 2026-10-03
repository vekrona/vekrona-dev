#!/usr/bin/env python3
import json
import os
import socket
import struct
import sys

MAGIC = b"i3-ipc"
HEADER = struct.Struct("=6sII")
SUBSCRIBE = 2


def read_exact(sock, size):
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("sway closed the IPC socket")
        data += chunk
    return data


def read_message(sock):
    magic, length, kind = HEADER.unpack(read_exact(sock, HEADER.size))
    if magic != MAGIC:
        raise ConnectionError(f"unexpected IPC magic {magic!r}")
    return kind, json.loads(read_exact(sock, length))


def main():
    events = sys.argv[1:]
    if not events:
        print("usage: sway-events.py EVENT...", file=sys.stderr)
        return 2
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(os.environ["SWAYSOCK"])
    payload = json.dumps(events).encode()
    sock.sendall(HEADER.pack(MAGIC, len(payload), SUBSCRIBE) + payload)
    _, reply = read_message(sock)
    if not reply.get("success"):
        print(f"sway refused the subscription to {events}: {reply}", file=sys.stderr)
        return 1
    print(json.dumps({"subscribed": events}), flush=True)
    while True:
        _, event = read_message(sock)
        print(json.dumps(event, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    sys.exit(main())
