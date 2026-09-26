"""Autonomous YouTube Shorts factory.

    python main.py auth       one-time YouTube OAuth consent
    python main.py once       produce and publish a single Short now
    python main.py schedule   publish one Short every day at SHORTS_POST_TIME (default)
"""

import argparse
import logging
import time

import anthropic
import schedule

from factory.agents import uploader
from factory.config import Settings
from factory.orchestrator import produce_short

log = logging.getLogger("factory")


def run_once(settings: Settings, client: anthropic.Anthropic) -> None:
    job = produce_short(settings, client)
    log.info("published https://youtube.com/shorts/%s (%s)", job.video_id, job.dir)


def run_scheduled(settings: Settings, client: anthropic.Anthropic) -> None:
    def job() -> None:
        try:
            run_once(settings, client)
        except Exception:
            # A failed run must not stop tomorrow's; the job directory is kept for inspection.
            log.exception("run failed")

    schedule.every().day.at(settings.post_time).do(job)
    log.info("scheduled daily at %s (niche: %s)", settings.post_time, settings.niche)
    while True:
        schedule.run_pending()
        time.sleep(30)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", nargs="?", choices=["auth", "once", "schedule"], default="schedule")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.command == "auth":
        uploader.authorize()
        return

    settings = Settings.from_env()
    client = anthropic.Anthropic()
    if args.command == "once":
        run_once(settings, client)
    else:
        run_scheduled(settings, client)


if __name__ == "__main__":
    main()
