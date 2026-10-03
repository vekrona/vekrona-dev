import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

QMP = Path(__file__).resolve().parents[1] / "lib" / "qmp.py"
_spec = importlib.util.spec_from_file_location("qmp", QMP)
qmp_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qmp_module)


class FakeQemu:
    def __init__(self, path):
        self.requests = []
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(path)
        self.server.listen(1)
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        try:
            connection, _ = self.server.accept()
        except OSError:
            return
        with connection, connection.makefile("rw", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps({"QMP": {"version": {}, "capabilities": []}}) + "\n")
            stream.flush()
            for line in stream:
                request = json.loads(line)
                self.requests.append(request)
                stream.write(json.dumps({"return": {}}) + "\n")
                stream.flush()

    def close(self):
        self.server.close()
        self.thread.join(timeout=10)


class QmpTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.sock = os.path.join(self.dir.name, "qmp.sock")
        self.qemu = FakeQemu(self.sock)
        self.addCleanup(self.qemu.close)

    def qmp(self, *args):
        result = subprocess.run([sys.executable, "-B", str(QMP), "--sock", self.sock, *args],
                                capture_output=True, text=True, timeout=30)
        self.qemu.close()
        return result

    def sent(self, command):
        return [r.get("arguments") for r in self.qemu.requests if r["execute"] == command]

    def test_holding_a_chord_leaves_the_release_to_qemu(self):
        self.assertEqual(self.qmp("hold", "super-shift-4", "1500").returncode, 0)
        keys = [{"type": "qcode", "data": q} for q in ("meta_l", "shift", "4")]
        self.assertEqual(self.sent("send-key"), [{"keys": keys, "hold-time": 1500}])

    def test_a_hold_must_last(self):
        for ms in ("0", "-1"):
            with self.subTest(ms=ms):
                result = subprocess.run([sys.executable, "-B", str(QMP), "--sock", self.sock, "hold", "esc", ms],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 1)
                self.assertIn("must be positive", result.stderr)

    def test_a_hold_time_must_be_a_number(self):
        result = subprocess.run([sys.executable, "-B", str(QMP), "--sock", self.sock, "hold", "esc", "lizard"],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2)

    def test_typing_presses_one_chord_per_character(self):
        self.assertEqual(self.qmp("type", "--enter", "Vk!").returncode, 0)
        chords = [[k["data"] for k in a["keys"]] for a in self.sent("send-key")]
        self.assertEqual(chords, [["shift", "v"], ["k"], ["shift", "1"], ["ret"]])

    def test_characters_without_a_key_are_refused(self):
        result = self.qmp("type", "é")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no keycode mapping", result.stderr)
        self.assertEqual(self.sent("send-key"), [])

    def test_a_missing_vm_is_reported(self):
        result = subprocess.run([sys.executable, "-B", str(QMP), "--sock", os.path.join(self.dir.name, "lizard.sock"),
                                 "key", "esc"], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot connect", result.stderr)

    def test_attaching_a_usb_device_adds_a_usb_host_device_with_a_stable_id(self):
        self.assertEqual(self.qmp("usb-attach", "1050:0407").returncode, 0)
        self.assertEqual(self.sent("device_add"), [{
            "driver": "usb-host", "bus": "usb-bus.0", "id": "hostusb-1050-0407",
            "vendorid": 0x1050, "productid": 0x0407,
        }])

    def test_detaching_a_usb_device_deletes_it_by_the_attach_id(self):
        self.assertEqual(self.qmp("usb-detach", "1050:0407").returncode, 0)
        self.assertEqual(self.sent("device_del"), [{"id": "hostusb-1050-0407"}])

    def test_the_usb_id_ignores_hex_case(self):
        self.assertEqual(qmp_module.usb_device_id("ABCD:00ef"), qmp_module.usb_device_id("abcd:00EF"))

    def test_a_usb_spec_must_be_vid_colon_pid_in_hex(self):
        self.assertEqual(qmp_module.parse_usb_spec("1050:0407"), (0x1050, 0x0407))
        for spec in ("", "lizard", "1050", "1050:04070", "zzzz:0407", "1050:0407:1"):
            with self.subTest(spec=spec):
                with self.assertRaises(qmp_module.QmpError):
                    qmp_module.parse_usb_spec(spec)

    def test_a_malformed_usb_spec_never_reaches_qemu(self):
        result = self.qmp("usb-attach", "lizard")
        self.assertEqual(result.returncode, 1)
        self.assertIn("VID:PID", result.stderr)
        self.assertEqual(self.sent("device_add"), [])


if __name__ == "__main__":
    unittest.main()
