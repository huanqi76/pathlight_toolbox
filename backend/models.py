from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from backend.database import Connection, async_session
from datetime import datetime
from typing import List, Optional
import csv
import os

class ConnectionService:
    @staticmethod
    async def add_connection(handle: str, company: str, date_scraped: Optional[datetime] = None):
        """Add a new connection, avoiding duplicates"""
        if date_scraped is None:
            date_scraped = datetime.utcnow()
            
        async with async_session() as session:
            # Check if connection already exists
            existing = await session.execute(
                select(Connection).where(
                    and_(Connection.handle == handle, Connection.company == company)
                )
            )
            
            if existing.scalar_one_or_none() is None:
                connection = Connection(
                    handle=handle,
                    company=company,
                    date_scraped=date_scraped
                )
                session.add(connection)
                await session.commit()
                return connection
            return None

    @staticmethod
    async def get_connections_by_handle(handle: str) -> List[Connection]:
        """Get all connections for a specific handle"""
        async with async_session() as session:
            result = await session.execute(
                select(Connection).where(Connection.handle == handle)
                .order_by(Connection.date_scraped.desc())
            )
            return result.scalars().all()

    @staticmethod
    async def get_all_connections() -> List[Connection]:
        """Get all connections"""
        async with async_session() as session:
            result = await session.execute(
                select(Connection).order_by(Connection.date_scraped.desc())
            )
            return result.scalars().all()

    @staticmethod
    async def migrate_from_csv(csv_filename: str = "results.csv"):
        """Migrate existing CSV data to PostgreSQL"""
        if not os.path.exists(csv_filename):
            return 0
            
        migrated_count = 0
        async with async_session() as session:
            with open(csv_filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Check if connection already exists
                    existing = await session.execute(
                        select(Connection).where(
                            and_(
                                Connection.handle == row["handle"],
                                Connection.company == row["company"]
                            )
                        )
                    )
                    
                    if existing.scalar_one_or_none() is None:
                        connection = Connection(
                            handle=row["handle"],
                            company=row["company"],
                            date_scraped=datetime.strptime(row["date"], "%Y-%m-%d")
                        )
                        session.add(connection)
                        migrated_count += 1
                        
            await session.commit()
        return migrated_count