import atexit
import hashlib
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent
DEBUG_PORT = 8000 + int(hashlib.md5(str(PROJECT_DIR).encode()).hexdigest(), 16) % 2000

from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from uvicorn.config import Config
from uvicorn.server import Server
from uvicorn.supervisors.watchfilesreload import WatchFilesReload


def create_application_with_static_handler() -> ASGIStaticFilesHandler:
    # Mirror runserver's static handler without editing server/asgi.py.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
    from server import asgi

    return ASGIStaticFilesHandler(asgi.application)


vite_proc: subprocess.Popen[bytes] | None = None
tsc_proc: subprocess.Popen[bytes] | None = None


def terminate_proc(proc: subprocess.Popen[Any]) -> None:
    """
    npm exec / npx don't always forward signals to their child processes.
    So just calling proc.terminate() may not kill everything.

    We instead send SIGTERM to the *process group*.

    NOTE: this assumes the Popen() call used start_new_session=True.
    """
    try:
        pgrp = os.getpgid(proc.pid)
    except ProcessLookupError:
        # Process already gone
        return

    # Send SIGTERM to the whole group
    os.killpg(pgrp, signal.SIGTERM)

    try:
        # Give it up to 5s to exit cleanly
        proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        # If it's still around, hard-kill
        proc.kill()


def get_free_port() -> int:
    """
    Bind to port 0 to let the OS choose an available port, then return it.
    """
    sock = socket.socket()
    try:
        sock.bind(("", 0))
        return sock.getsockname()[1]  # type: ignore[no-any-return]
    finally:
        sock.close()


def cleanup() -> None:
    print("Running atexit cleanup…")
    for name, proc in (("vite", vite_proc), ("tsc", tsc_proc)):
        if proc is None:
            print(f"Process {name} is None")
            continue

        if proc.poll() is None:  # still running
            print(f"Terminating {name} process group…")
            try:
                terminate_proc(proc)
            except Exception as e:  # noqa: BLE001
                print(f"Error while terminating {name}: {e!r}")
        else:
            print(f"Process {name} is already terminated (code={proc.returncode})")
    print("Cleanup done.")


atexit.register(cleanup)


def generate_client_assets(*, wait: bool = False) -> None:
    process = subprocess.Popen(
        ["python", "manage.py", "generate_client_assets", "--cached"],
    )
    if wait:
        process.wait()


class SmartChangeReload(WatchFilesReload):
    def should_restart(self) -> list[Path] | None:
        changes = super().should_restart()

        if changes:
            print(f"Changes detected: {changes}")
            generate_client_assets()
        return changes


if __name__ == "__main__":
    generate_client_assets(wait=False)

    client_port = str(DEBUG_PORT)
    backend_port = get_free_port()

    os.environ["REACTIVATED_VITE_PORT"] = str(client_port)
    os.environ["REACTIVATED_DJANGO_PORT"] = str(backend_port)

    static_url = "/static/"

    vite_proc = subprocess.Popen(
        ["npm", "exec", "start_vite"],
        env={**os.environ.copy(), "BASE": f"{static_url}dist/"},
        start_new_session=True,
    )

    # npm exec is weird and seems to run into duplicate issues if executed
    # too quickly. There are better ways to do this, I assume.
    time.sleep(0.5)

    tsc_proc = subprocess.Popen(
        [
            "npm",
            "exec",
            "tsc",
            "--",
            "--watch",
            "--noEmit",
            "--preserveWatchOutput",
        ],
        env={**os.environ.copy()},
        start_new_session=True,
    )
    os.environ["REACTIVATED_RENDERER"] = f"http://localhost:{client_port}"

    print(f"\n  Dev server: \033[1;36mhttp://localhost:{client_port}/\033[0m\n")

    config = Config(
        "dev:create_application_with_static_handler",
        host="127.0.0.1",
        factory=True,
        reload=True,
        port=backend_port,
        log_level="info",
        timeout_graceful_shutdown=0,
        reload_excludes=[
            "server/**/tests/**",
            "server/**/pytests.py",
        ],
    )
    server = Server(config)
    sock = config.bind_socket()
    SmartChangeReload(config, target=server.run, sockets=[sock]).run()
