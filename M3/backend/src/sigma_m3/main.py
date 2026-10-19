"""Local API foundation. No request performs model fitting or raw-file upload."""
from contextlib import asynccontextmanager
import uuid
from fastapi import FastAPI, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sigma_m3.db import database
from sigma_m3.errors import DomainError
from sigma_m3.models import Warehouse, Item, Supplier, Policy, Run
from sigma_m3.schemas import PolicyCreate, RunCreate
from sigma_m3.services.catalog import create_policy
from sigma_m3.services.runs import enqueue, required_run
from sigma_m3.settings import Settings


def record(row):
    return {c.name:getattr(row,c.name) for c in row.__table__.columns}


def run_view(row):
    # Detailed config, manifest file paths and request payload are private.
    return {name:getattr(row,name) for name in ['id','kind','status','source_import_run_id','forecast_run_id',
        'scenario_id','as_of_date','observation_end','config_version','assumption_version','target_version',
        'created_at','started_at','finished_at','heartbeat_at','error_code','result_summary']}


def create_app(settings=None):
    settings = settings or Settings.from_env()
    engine, sessions = database(settings.database_url)
    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()
    app = FastAPI(title='SIGMA M3 local API', version='0.1.0', lifespan=lifespan)
    app.state.engine, app.state.sessions, app.state.settings = engine, sessions, settings
    app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin],
                       allow_methods=['GET','POST','PATCH'],allow_headers=['Content-Type','Idempotency-Key'])

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return JSONResponse(status_code=exc.status,content={'error':dict(code=exc.code,message=exc.message,details=exc.details),'request_id':str(uuid.uuid4())})

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        # Pydantic's default error can echo submitted values. Return field/type only.
        return JSONResponse(status_code=422,content={'error':{'code':'invalid_input','message':'Invalid request fields',
            'details':{'fields':[{'location':list(e['loc']),'type':e['type']} for e in exc.errors()]}},'request_id':str(uuid.uuid4())})

    @app.exception_handler(IntegrityError)
    async def integrity(request, exc):
        return await domain_error(request,DomainError('version_conflict','Database constraint rejected the change',409))

    @app.exception_handler(OperationalError)
    async def unavailable(request, exc):
        return await domain_error(request,DomainError('database_unavailable','Database is unavailable',503))

    @app.get('/api/v1/health')
    def health():
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        return {'status':'ok','database':'reachable','profile':'m3-design-v1'}

    def listing(model, page, size, predicates=()):
        with sessions() as session:
            query = select(model).where(*predicates)
            total = session.scalar(select(func.count()).select_from(query.subquery()))
            rows = session.scalars(query.order_by(model.id).offset((page-1)*size).limit(size)).all()
            return {'items':[record(r) for r in rows],'total':total,'page':page,'page_size':size}

    @app.get('/api/v1/warehouses')
    def warehouses(page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=100),country:str|None=None):
        return listing(Warehouse,page,page_size,[Warehouse.destination_country==country] if country else [])

    @app.get('/api/v1/items')
    def items(page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=100),warehouse_id:int|None=Query(None,gt=0),product_type:str|None=None):
        filters=[]
        if warehouse_id:filters.append(Item.warehouse_id==warehouse_id)
        if product_type:filters.append(Item.product_type==product_type)
        return listing(Item,page,page_size,filters)

    @app.get('/api/v1/suppliers')
    def suppliers(page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=100)):
        return listing(Supplier,page,page_size)

    @app.get('/api/v1/supplier-item-policies')
    def policies(item_id:int|None=None,page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=100)):
        return listing(Policy,page,page_size,[Policy.item_id==item_id] if item_id else [])

    @app.post('/api/v1/supplier-item-policies',status_code=201)
    def policy(request:PolicyCreate):
        with sessions.begin() as session:
            row = create_policy(session,request)
            return jsonable_encoder(record(row))

    @app.post('/api/v1/runs')
    def runs_post(request:RunCreate,idempotency_key:str=Header(alias='Idempotency-Key')):
        with sessions.begin() as session:
            row,created=enqueue(session,request,idempotency_key)
            return JSONResponse(status_code=202 if created else 200,content=jsonable_encoder(dict(run_id=row.id,
                status=row.status,status_url=f'/api/v1/runs/{row.id}')))

    @app.get('/api/v1/runs')
    def runs_get(page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=100)):
        with sessions() as session:
            rows=session.scalars(select(Run).order_by(Run.created_at.desc(),Run.id).offset((page-1)*page_size).limit(page_size)).all()
            return dict(items=[run_view(r) for r in rows],total=session.scalar(select(func.count()).select_from(Run)),page=page,page_size=page_size)

    @app.get('/api/v1/runs/{key}')
    def run_get(key:uuid.UUID):
        with sessions() as session:
            return run_view(required_run(session,key))

    @app.get('/api/v1/runs/{key}/summary')
    def run_summary(key:uuid.UUID):
        with sessions() as session:
            row=required_run(session,key,complete=True)
            return dict(context=run_view(row),summary=row.result_summary)
    return app
