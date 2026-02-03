from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    MetaData,
    String,
    Table,
    create_engine,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

metadata = MetaData()

configs = Table(
    "configs",
    metadata,
    Column("config_id", UUID(as_uuid=False), primary_key=True),  # app側でUUID文字列を入れる
    Column("kind", String, nullable=False),
    Column("name", String, nullable=False),
    Column("spec", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("meta", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
)

# 注意:
# UNIQUE(kind, name) がDB側にある前提。なければ upsert が効かない。


@dataclass
class PostgresConfigStore:
    database_url: str

    def __post_init__(self) -> None:
        self.engine: Engine = create_engine(self.database_url, future=True)

    def get_spec(self, kind: str, name: str) -> dict[str, Any]:
        stmt = (
            select(configs.c.spec)
            .where(configs.c.kind == kind)
            .where(configs.c.name == name)
            .where(configs.c.is_active.is_(True))
            .limit(1)
        )
        with self.engine.begin() as conn:
            row = conn.execute(stmt).fetchone()
        if row is None:
            raise KeyError(f"config not found: kind={kind} name={name}")
        # row[0] is JSONB -> dict
        return dict(row[0])

    def put_spec(self, kind: str, name: str, spec: dict[str, Any], *, config_id: str) -> None:
        stmt = (
            pg_insert(configs)
            .values(
                config_id=config_id,
                kind=kind,
                name=name,
                spec=spec,
                meta={},
                is_active=True,
            )
            .on_conflict_do_update(
                index_elements=[configs.c.kind, configs.c.name],
                set_={
                    "spec": spec,
                    "is_active": True,
                    "updated_at": text("now()"),
                },
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
