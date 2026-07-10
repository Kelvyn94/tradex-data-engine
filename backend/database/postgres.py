"""
PostgreSQL database connection for TradeX Data Engine.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator, Optional
import logging

from backend.config.settings import settings
from backend.database.models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages PostgreSQL database connections."""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the database engine."""
        try:
            self.engine = create_engine(
                settings.DATABASE_URL,
                poolclass=QueuePool,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,
                echo=False
            )
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            logger.info("Database engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def create_tables(self):
        """Create all tables if they don't exist."""
        try:
            # Create schema if not exists using SQLAlchemy text()
            with self.engine.connect() as conn:
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS data_engine"))
                conn.commit()
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with context manager."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """Get a database session synchronously."""
        return self.SessionLocal()

# Create global database manager instance
db_manager = DatabaseManager()

# Initialize tables on import
try:
    db_manager.create_tables()
except Exception as e:
    logger.warning(f"Could not create tables: {e}")