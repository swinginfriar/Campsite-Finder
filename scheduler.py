#!/usr/bin/env python3
"""
scheduler.py — Docker-friendly replacement for the cron the README describes.

Runs the CampSage scan (camp_agent) immediately on start, optionally fetches
Wikimedia photos, then sleeps and repeats. All knobs (scan interval, whether to
fetch photos, home base, radius, …) come from the web UI at /camp/settings,
persisted to settings.json — this loop re-reads them via config.reload() before
every scan, so UI edits take effect on the next run with NO env vars to set.

Between scans it polls for a "scan now" request file (written by the Settings
page's Save & scan now button) so edits can apply immediately instead of waiting
out the interval.
"""
import sys
import time
import traceback
from datetime import datetime

import config

POLL_SECONDS = 15   # how often, mid-sleep, to check for a "scan now" request


def _log(msg):
    print(f"[scheduler {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def _clear_rescan_request():
    try:
        config.RESCAN_REQUEST.unlink()
    except FileNotFoundError:
        pass
    except Exception:
        pass


def _run_scan():
    config.reload()   # pick up any settings.json edits made in the UI
    import camp_agent
    camp_agent.run()

    if config.FETCH_IMAGES:
        try:
            import runpy
            _log("fetching Wikimedia photos …")
            runpy.run_module("camp_wiki_images", run_name="__main__")
        except Exception:
            _log("photo fetch failed (non-fatal):")
            traceback.print_exc()


def _sleep_until_next(interval_hours, started):
    """Sleep in short polls until the interval elapses OR a scan-now is requested."""
    interval_s = max(60.0, interval_hours * 3600)
    while True:
        elapsed = time.time() - started
        if elapsed >= interval_s:
            return
        if config.RESCAN_REQUEST.exists():
            _log("scan-now requested from the UI.")
            _clear_rescan_request()
            return
        time.sleep(min(POLL_SECONDS, interval_s - elapsed))


def main():
    _clear_rescan_request()   # ignore any stale request from a previous run
    while True:
        started = time.time()
        try:
            _log("starting scan …")
            _run_scan()
            _log("scan complete.")
        except Exception:
            _log("scan FAILED:")
            traceback.print_exc()

        config.reload()
        interval_h = config.SCAN_INTERVAL_HOURS
        _log(f"next scan in ~{interval_h:g}h (or when requested from the UI)")
        _sleep_until_next(interval_h, started)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
