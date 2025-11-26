from pathlib import Path

from sqlalchemy import Engine as SQLEngine
from sqlalchemy import create_engine

from zeni.database.models import Base
from zeni.database.utils import DEFAULT_PATHWAY, sql_directory


class Engine:
    def __init__(
        self, name: str, pathway: Path | str = DEFAULT_PATHWAY, echoes: bool = False
    ):
        self.name = name
        self.pathway = pathway
        self.echoes = echoes

        self._db = sql_directory(self.pathway, self.name)

        self._engine: SQLEngine | None = None

    def create(self) -> SQLEngine:
        """Create and return a sqlalchemy Engine for a database.

        Returns
        -------
        SQLEngine
        """
        self._engine = create_engine(self._db, echo=self.echoes)
        Base.metadata.create_all(self._engine)
        return self._engine

    def close_connections(self) -> None:
        """Close all connections."""
        if self._engine:
            self._engine.dispose()

    def delete(self) -> None:
        """Delete the database file if it exists."""
        db_file = self._db.replace("sqlite:///", "")
        db_path = Path(db_file)
        db_path.unlink(missing_ok=True)
