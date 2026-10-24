"""Shared engine/session and the single SQLAlchemy model metadata."""
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Identity, create_engine, func
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def identity():
    return Column(BigInteger, Identity(always=True), primary_key=True)


def fk(table, nullable=False):
    return Column(
        BigInteger, ForeignKey(table + ".id", ondelete="RESTRICT"), nullable=nullable
    )


def created():
    return Column(DateTime(timezone=True), nullable=False, server_default=func.now())


def database(url):
    if not url.startswith("postgresql+psycopg://"):
        raise ValueError("M3 requires PostgreSQL; SQLite cannot verify this schema")
    engine = create_engine(
        url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )
    return engine, sessionmaker(engine, expire_on_commit=False)
