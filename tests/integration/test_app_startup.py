from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunningProcess:
    proc: subprocess.Popen[str]
    lines: list[str]
    thread: threading.Thread


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _pythonpath_for_subprocess(repo_root: Path) -> str:
    src = str(repo_root / "src")
    existing = os.environ.get("PYTHONPATH")
    return src if not existing else os.pathsep.join([src, existing])


def _start_callscribe(*, repo_root: Path, run_for_ms: int, instance_id: str) -> RunningProcess:
    env = dict(os.environ)
    env["CALLSCRIBE_INSTANCE_ID"] = instance_id
    env["CALLSCRIBE_TEST_MODE"] = "1"
    env["CALLSCRIBE_LOG_STDOUT"] = "1"
    env["CALLSCRIBE_TEST_RUN_FOR_MS"] = str(run_for_ms)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = _pythonpath_for_subprocess(repo_root)

    proc = subprocess.Popen(
        [sys.executable, "-m", "callscribe"],
        cwd=str(repo_root),
        env=env,
        text=True,
        bufsize=1,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert proc.stdout is not None
    stdout = proc.stdout

    lines: list[str] = []

    def reader() -> None:
        for line in stdout:
            lines.append(line.rstrip("\n"))

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    # Let the reader thread start before the child prints the first log line (Windows pipe race).
    time.sleep(0.05)
    return RunningProcess(proc=proc, lines=lines, thread=t)


def _wait_for_line(lines: list[str], prefix: str, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if any(line.startswith(prefix) for line in lines):
            return True
        time.sleep(0.02)
    return False


def test_second_launch_activates_existing_instance() -> None:
    repo_root = _repo_root()
    instance_id = f"callscribe_itest_{uuid.uuid4().hex[:10]}"

    first = _start_callscribe(repo_root=repo_root, run_for_ms=4000, instance_id=instance_id)
    try:
        assert _wait_for_line(
            first.lines,
            "CALLSCRIBE_READY",
            timeout_s=25.0,
        ), "\n".join(first.lines) or f"(no stdout; poll={first.proc.poll()})"

        second = _start_callscribe(repo_root=repo_root, run_for_ms=1000, instance_id=instance_id)
        try:
            second_exit = second.proc.wait(timeout=25.0)
            assert second_exit == 0, "\n".join(second.lines)
            assert any(
                line.startswith("CALLSCRIBE_ALREADY_RUNNING")
                for line in second.lines
            ), "\n".join(second.lines)

            assert _wait_for_line(
                first.lines,
                "CALLSCRIBE_ACTIVATED",
                timeout_s=15.0,
            ), "\n".join(first.lines)
        finally:
            if second.proc.poll() is None:
                second.proc.terminate()
                try:
                    second.proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    second.proc.kill()
    finally:
        if first.proc.poll() is None:
            first.proc.terminate()
            try:
                first.proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                first.proc.kill()
