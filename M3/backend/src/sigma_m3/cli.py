"""CLI and API share the same validation, idempotency and run services."""
import argparse,json,uuid
from datetime import date
from sqlalchemy import select
from sigma_m3.db import database
from sigma_m3.models import Run
from sigma_m3.schemas import RunCreate
from sigma_m3.services.runs import enqueue,required_run
from sigma_m3.settings import Settings
from sigma_m3.worker import serve


def main():
    p=argparse.ArgumentParser()
    commands=p.add_subparsers(dest='command',required=True)
    imp=commands.add_parser('import-orders');imp.add_argument('--source-key',default='orders_snapshot',choices=['orders_snapshot'])
    imp.add_argument('--as-of-date',default='2025-12-31');imp.add_argument('--request-key');imp.add_argument('--wait',action='store_true')
    status=commands.add_parser('status');status.add_argument('--run-id',type=uuid.UUID,required=True)
    seed=commands.add_parser('seed-simulation');seed.add_argument('--source-run',type=uuid.UUID,required=True);seed.add_argument('--as-of-date',type=date.fromisoformat,required=True)
    args=p.parse_args();settings=Settings.from_env();engine,sessions=database(settings.database_url)
    try:
        if args.command=='seed-simulation':
            from sigma_m3.services.seeding import seed_simulation
            with sessions.begin() as session:result=seed_simulation(session,args.source_run,args.as_of_date)
            print(json.dumps(result));return
        if args.command=='import-orders':
            with sessions.begin() as session:
                row,_=enqueue(session,RunCreate(kind='source_import',as_of_date=args.as_of_date,source_key=args.source_key),args.request_key or str(uuid.uuid4()))
                key=row.id
            if args.wait:
                # Run the ordinary locked worker. Existing earlier queue entries are processed first.
                while True:
                    with sessions() as session:
                        state=required_run(session,key).status
                    if state in {'complete','failed','invalidated'}:break
                    serve(settings,once=True)
                if state!='complete':raise SystemExit('Run did not complete; inspect status/error_code')
        else:key=args.run_id
        with sessions() as session:
            row=required_run(session,key)
            print(json.dumps({'run_id':str(row.id),'kind':row.kind,'status':row.status,'error_code':row.error_code,'summary':row.result_summary},default=str))
    finally:engine.dispose()


if __name__=='__main__':main()
