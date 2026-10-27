"""Local, explicit reconciliation of a failed and safely cleaned-up Studio build."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Integracja'))
from rockpro_cad import studio_cad_jobs
from rockpro_cad.mcp import project_store


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--operation', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        database = args.database.resolve(strict=True)
        if not database.is_file():
            raise ValueError('Expected existing database')
        project_store.DB_PATH = database
        result = studio_cad_jobs.reconcile_failed_job(args.operation, args.evidence)
    except studio_cad_jobs.CadJobError as error:
        print(json.dumps(error.details, ensure_ascii=False)); return 1
    except Exception:
        print(json.dumps(dict(code='CAD_RECONCILE_UNAVAILABLE', message=
            'Nie można uzgodnić zlecenia. Sprawdź jawną bazę danych, dowody i dostępność blokady CAD.'), ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
