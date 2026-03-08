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
    Text,
    create_engine,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from flowbook.core.configs.store import ConfigStore

metadata = MetaData()

configs = Table(
    "configs",
    metadata,
    Column("config_id", UUID(as_uuid=False), primary_key=True),
    Column("config_type", String, nullable=False),
    Column("config_name", String, nullable=False),
    Column("spec", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("spec_text", Text, nullable=True, server_default=text("''")),
    Column("meta", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
)


@dataclass
class PostgresConfigStore(ConfigStore):
    database_url: str

    def __post_init__(self) -> None:
        self.engine: Engine = create_engine(self.database_url, future=True)

    def _get_spec_by_config_type(self, config_type: str, config_name: str) -> dict[str, Any]:
        doc = self.get_config_document(config_type, config_name)
        return doc["spec"]

    def get_config_document(self, config_type: str, config_name: str) -> dict[str, Any]:
        stmt = (
            select(configs.c.spec, configs.c.spec_text)
            .where(configs.c.config_type == config_type)
            .where(configs.c.config_name == config_name)
            .where(configs.c.is_active.is_(True))
            .limit(1)
        )
        with self.engine.begin() as conn:
            row = conn.execute(stmt).fetchone()
        if row is None:
            raise KeyError(f"config not found: config_type={config_type} config_name={config_name}")
        spec, spec_text = row[0], row[1]
        return {"spec": dict(spec), "spec_text": spec_text or ""}

    def _put_spec_by_config_type(
        self,
        config_type: str,
        config_name: str,
        spec: dict[str, Any],
        *,
        config_id: str,
        spec_text: str = "",
    ) -> None:
        stmt = (
            pg_insert(configs)
            .values(
                config_id=config_id,
                config_type=config_type,
                config_name=config_name,
                spec=spec,
                spec_text=spec_text or "",
                meta={},
                is_active=True,
            )
            .on_conflict_do_update(
                index_elements=[configs.c.config_type, configs.c.config_name],
                set_={
                    "spec": spec,
                    "spec_text": spec_text or "",
                    "is_active": True,
                    "updated_at": text("now()"),
                },
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
