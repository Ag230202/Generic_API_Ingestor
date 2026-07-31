from typing import List, Dict, Any, Optional
import logging
from sqlalchemy import MetaData, Table, Column, String, Text, Integer, Float, Boolean, DateTime, select
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.storage.base import BaseStorage

logger = logging.getLogger(__name__)


class PostgresStorage(BaseStorage):
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.metadata = MetaData()

    def _infer_sql_type(self, value: Any):
        if isinstance(value, int):
            return Integer
        elif isinstance(value, float):
            return Float
        elif isinstance(value, bool):
            return Boolean
        elif isinstance(value, str):
            return Text
        else:
            return Text

    async def _ensure_table_exists(
        self,
        conn,
        table_name: str,
        sample_record: Dict[str, Any],
        primary_key: Optional[str] = None
    ) -> Table:
        # Reflect existing table if already present
        def get_table(connection):
            meta = MetaData()
            meta.reflect(bind=connection)
            if table_name in meta.tables:
                return meta.tables[table_name]
            return None

        existing_table = await conn.run_sync(get_table)
        if existing_table is not None:
            return existing_table

        columns = []
        for col_name, value in sample_record.items():
            is_pk = (col_name == primary_key)
            col_type = self._infer_sql_type(value)
            columns.append(Column(col_name, col_type, primary_key=is_pk, nullable=not is_pk))

        # Ensure ID column exists if no primary key specified
        if not primary_key and "_id" not in sample_record:
            columns.append(Column("_id", Integer, primary_key=True, autoincrement=True))

        new_table = Table(table_name, self.metadata, *columns)

        def create_all(connection):
            self.metadata.create_all(bind=connection)

        await conn.run_sync(create_all)
        logger.info(f"Created dynamic PostgreSQL table: '{table_name}'")
        return new_table

    async def save_records(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        primary_key: Optional[str] = None
    ) -> int:
        if not records:
            return 0

        async with self.engine.begin() as conn:
            sample_record = records[0]
            table = await self._ensure_table_exists(conn, table_name, sample_record, primary_key)

            # Build insert statements
            for record in records:
                # Clean keys matching table columns
                record_data = {k: v for k, v in record.items() if k in table.columns}
                
                stmt = pg_insert(table).values(record_data)
                if primary_key and primary_key in record_data:
                    # Upsert on primary key conflict
                    update_dict = {k: v for k, v in record_data.items() if k != primary_key}
                    if update_dict:
                        stmt = stmt.on_conflict_do_update(
                            index_elements=[primary_key],
                            set_=update_dict
                        )
                    else:
                        stmt = stmt.on_conflict_do_nothing(index_elements=[primary_key])
                else:
                    stmt = stmt.on_conflict_do_nothing()

                await conn.execute(stmt)

        logger.info(f"Successfully saved {len(records)} records into table '{table_name}'")
        return len(records)
