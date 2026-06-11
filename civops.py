#!/usr/bin/env python3
# civops.py
import argparse
import shutil
from datetime import datetime
from pathlib import Path
from storage.database import Database
from storage.logger import JSONLLogger
from ui.app import CivopsApp


def _detect_backend():
    if shutil.which("termux-wifi-scaninfo"):
        from backends.termux import TermuxBackend
        return TermuxBackend()
    from backends.linux import LinuxBackend
    return LinuxBackend()


def main():
    parser = argparse.ArgumentParser(description="CIVOPS Recon Radar")
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Scan interval in seconds (default: 5)")
    parser.add_argument("--backend", choices=["termux", "linux"],
                        help="Force backend (default: auto-detect)")
    parser.add_argument("--db",
                        default=str(Path.home() / "civops-data" / "civops.db"),
                        help="SQLite database path")
    parser.add_argument("--web", action="store_true",
                        help="Run web UI instead of TUI (open in Chrome)")
    parser.add_argument("--port", type=int, default=8080,
                        help="Web server port (default: 8080)")
    args = parser.parse_args()

    if args.backend == "termux":
        from backends.termux import TermuxBackend
        backend = TermuxBackend()
    elif args.backend == "linux":
        from backends.linux import LinuxBackend
        backend = LinuxBackend()
    else:
        backend = _detect_backend()

    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    db = Database(args.db)
    session_id = db.create_session()

    ts = datetime.now().strftime("%Y-%m-%d-%H-%M")
    log_path = str(Path.home() / "civops-data" / f"civops-{ts}.jsonl")
    logger = JSONLLogger(log_path)

    if args.web:
        from ui.web import WebUI
        ui = WebUI(backend=backend, db=db, logger=logger,
                   session_id=session_id, scan_interval=args.interval)
        ui.run(port=args.port)
    else:
        app = CivopsApp(
            backend=backend, db=db, logger=logger,
            session_id=session_id, scan_interval=args.interval,
        )
        app.run()

    db.close_session(session_id, kml_path="", gpx_path="")
    db.close()


if __name__ == "__main__":
    main()
