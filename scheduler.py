#!/usr/bin/env python3
"""
scheduler.py — Docker-friendly replacement for the cron the README describes.

Runs the CampSage scan (camp_agent) immediately on start, optionally fetches
Wikimedia photos, then sleeps and repeats forever. This is what the `scanner`
service runs in docker-compose so results stay fresh without a host crontab.

Tunables (env):
  CAMPSAGE_SCAN_INTERVAL_HOURS   how long to sleep between scans (default 6)
  CAMPSAGE_FETCH_IMAGES          "1"/"true" to also run camp_wiki_images (default on)
  CAMPSAGE_RUN_ONCE             "1"/"true" to scan once and exit (default off)
"""
import os
import sys
import time
import traceback
from datetime import datetime


def _bool(name, default):
    v = os.environ.get(name)
    if v in (None, ""):
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _log(msg):
    print(f"[scheduler {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def _run_scan():
    # Imported lazily so a crash in one module doesn't stop the loop from retrying.
    import camp_agent
    camp_agent.run()

    if _bool("CAMPSAGE_FETCH_IMAGES", True):
        try:
            import runpy
            _log("fetching Wikimedia photos …")
            runpy.run_module("camp_wiki_images", run_name="__main__")
        except Exception:
            _log("photo fetch failed (non-fatal):")
            traceback.print_exc()


def main():
    interval_h = float(os.environ.get("CAMPSAGE_SCAN_INTERVAL_HOURS", "6"))
    run_once = _bool("CAMPSAGE_RUN_ONCE", False)

    while True:
        started = time.time()
        try:
            _log("starting scan …")
            _run_scan()
            _log("scan complete.")
        except Exception:
            _log("scan FAILED:")
            traceback.print_exc()

        if run_once:
            _log("CAMPSAGE_RUN_ONCE set — exiting after one scan.")
            return

        elapsed = time.time() - started
        sleep_s = max(60.0, interval_h * 3600 - elapsed)
        _log(f"next scan in {sleep_s / 3600:.2f}h")
        time.sleep(sleep_s)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
