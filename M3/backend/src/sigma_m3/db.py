from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def database(url):
    if not url.startswith("postgresql+psycopg://"):
        raise ValueError("M3 requires PostgreSQL; SQLite cannot verify this schema")
    engine = create_engine(url, pool_pre_ping=True, hide_parameters=True,
                           connect_args={"connect_timeout": 5})
    return engine, sessionmaker(engine, expire_on_commit=False)
