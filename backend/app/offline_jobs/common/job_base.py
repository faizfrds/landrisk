"""Shared CLI boilerplate for offline hazard jobs.

Each hazard job is a plain script run manually:
    python -m app.offline_jobs.<hazard>.<module> --start-date 2015-01-01 --end-date 2026-01-01

None of these are wired to a scheduler -- rerunning on new data releases is
a manual/cron decision left to the operator (out of scope for this pass).
"""

import argparse
import logging
from dataclasses import dataclass, field
from datetime import date


def build_arg_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--h3-resolution", type=int, default=10)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and log results without writing to BigQuery.",
    )
    return parser


def configure_logging() -> logging.Logger:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return logging.getLogger("offline_job")


@dataclass
class JobRunSummary:
    hazard: str
    cells_processed: int = 0
    no_data_count: int = 0
    evidence_rows_written: int = 0
    warnings: list[str] = field(default_factory=list)

    def log(self, logger: logging.Logger) -> None:
        logger.info(
            "%s job done: %d cells processed, %d marked no_data, %d evidence rows written",
            self.hazard,
            self.cells_processed,
            self.no_data_count,
            self.evidence_rows_written,
        )
        for warning in self.warnings:
            logger.warning(warning)
