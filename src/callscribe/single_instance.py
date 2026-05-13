from __future__ import annotations

import atexit
import os
import socket
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ActivationHandler = Callable[[], None]

_ACTIVATION_REQUEST = b"CALLSCRIBE_ACTIVATE\n"
_ACTIVATION_RESPONSE = b"OK\n"


@dataclass(frozen=True)
class SingleInstanceGuard:
    _lock_path: Path
    _server: socket.socket
    _stop: threading.Event

    def close(self) -> None:
        self._stop.set()
        try:
            self._server.close()
        finally:
            try:
                self._lock_path.unlink(missing_ok=True)
            except OSError:
                # Best-effort cleanup; stale locks are handled on next start.
                return


def _lock_path_for(app_id: str) -> Path:
    safe = (
        "".join(
            ch if ch.isalnum() or ch in ("-", "_") else "_"
            for ch in app_id
        ).strip("_")
        or "app"
    )
    return Path(tempfile.gettempdir()) / f"{safe}.single_instance.lock"


def _try_activate_existing(lock_path: Path) -> bool:
    """Connect to primary port from lock file; retry briefly if the file is not filled yet."""
    port: int | None = None
    for _ in range(200):
        try:
            data = lock_path.read_text(encoding="utf-8").strip()
            if not data:
                time.sleep(0.05)
                continue
            port = int(data)
            break
        except ValueError:
            time.sleep(0.05)
            continue
        except OSError:
            return False
    if port is None:
        return False

    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5) as s:
            s.settimeout(0.5)
            s.sendall(_ACTIVATION_REQUEST)
            resp = s.recv(16)
        return resp.startswith(_ACTIVATION_RESPONSE)
    except OSError:
        return False


def _serve_activation(
    server: socket.socket,
    stop: threading.Event,
    on_activate: ActivationHandler,
) -> None:
    while not stop.is_set():
        try:
            server.settimeout(0.25)
            conn, _addr = server.accept()
        except TimeoutError:
            continue
        except OSError:
            return

        with conn:
            try:
                conn.settimeout(0.25)
                data = conn.recv(1024)
            except OSError:
                continue

            if not data.startswith(_ACTIVATION_REQUEST):
                continue

            try:
                on_activate()
            except Exception:
                # Activation is best-effort; never crash the tray process.
                continue

            try:
                conn.sendall(_ACTIVATION_RESPONSE)
            except OSError:
                continue


def ensure_single_instance(
    app_id: str,
    *,
    on_activate: ActivationHandler,
) -> SingleInstanceGuard | None:
    """
    Returns a guard for the primary instance, or None if activation was sent to an
    existing instance.

    Implementation is intentionally cross-platform:
    - A temp-dir lock file stores a localhost TCP port for activation.
    - Secondary instances connect to that port and send an activation message.
    """

    lock_path = _lock_path_for(app_id)

    for _ in range(2):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            port = int(server.getsockname()[1])
        except OSError:
            try:
                server.close()
            except OSError:
                pass
            continue

        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                server.close()
            except OSError:
                pass
            if _try_activate_existing(lock_path):
                return None
            time.sleep(0.15)
            if _try_activate_existing(lock_path):
                return None
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                return None
            continue

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(str(port))
                f.flush()
        except OSError:
            try:
                server.close()
            except OSError:
                pass
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass
            continue

        stop = threading.Event()
        t = threading.Thread(
            target=_serve_activation,
            args=(server, stop, on_activate),
            daemon=True,
        )
        t.start()

        guard = SingleInstanceGuard(
            _lock_path=lock_path,
            _server=server,
            _stop=stop,
        )
        atexit.register(guard.close)
        return guard

    return None

