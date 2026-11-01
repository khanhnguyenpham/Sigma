"""Preview/apply CHG-081 seed renames after backing up the local database.

Run from the project root with the existing environment loaded. This changes
only declared legacy seed labels, provenance and optimistic-lock versions.
It never rewrites frozen runs, inventory or private artifacts.
"""
import argparse
import json

from core.db import database
from core.settings import Settings
from modules.catalog.service import rename_seed_cities


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    engine, sessions = database(Settings.from_env().database_url)
    try:
        with sessions.begin() as session:
            result = rename_seed_cities(session, args.apply)
        print(json.dumps(result))
    finally:
        engine.dispose()
