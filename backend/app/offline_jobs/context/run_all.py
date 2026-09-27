"""Run offline jobs in dependency order: context first (parcels/FEMA zones
must exist before hazard jobs can be usefully aggregated per-parcel), then
the 5 hazard jobs.

Usage:
    python -m app.offline_jobs.context.run_all --start-date 2015-01-01 --end-date 2026-01-01 [--dry-run]
"""

import argparse
from datetime import date

from app.offline_jobs.context import fema_flood_zones, parcels_ingest
from app.offline_jobs.flood import sentinel1_flood
from app.offline_jobs.heat import landsat_lst
from app.offline_jobs.landuse import alphaearth_embeddings
from app.offline_jobs.subsidence import opera_subsidence
from app.offline_jobs.wildfire import firms_viirs, mtbs_burns


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all offline jobs in dependency order")
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("== context: parcels ==")
    parcels_ingest.ingest(dry_run=args.dry_run)

    print("== context: FEMA flood zones ==")
    fema_flood_zones.main()

    print("== flood ==")
    sentinel1_flood.run(args.start_date, args.end_date, 10, args.dry_run)

    print("== subsidence ==")
    opera_subsidence.run(args.start_date, args.end_date, 10, args.dry_run)

    print("== wildfire: FIRMS ==")
    firms_viirs.run(args.start_date, args.end_date, 10, args.dry_run)

    print("== wildfire: MTBS ==")
    mtbs_burns.run(10, args.dry_run)

    print("== heat ==")
    landsat_lst.run(args.start_date, args.end_date, 10, args.dry_run)

    print("== land-use change ==")
    alphaearth_embeddings.run(args.start_date, args.end_date, 10, args.dry_run)


if __name__ == "__main__":
    main()
