"""Engines for database instances."""

from pathlib import Path

from sqlalchemy import Engine as SQLEngine
from sqlalchemy import create_engine

from zeni.database.models import ZeniBase
from zeni.database.utils import DEFAULT_PATHWAY, sql_directory


class Engine:
    """A wrapper around SQLAlchemy Engine.

    Parameters
    ----------
    name: str
        The name of the database.
    pathway: Path | str
        The pathway to store this database, by default
            zeni.database.utils.DEFAULT_PATHWAY.
    echoes: bool
        Boolean flag for SQLAlchemy logging, by default False.
    """

    def __init__(
        self, name: str, pathway: Path | str = DEFAULT_PATHWAY, echoes: bool = False
    ):
        self.name = name
        self.pathway = pathway
        self.echoes = echoes

        self._db = sql_directory(self.pathway, self.name)
        self._sql: SQLEngine = create_engine(self._db, echo=self.echoes)
        ZeniBase.metadata.create_all(self._sql)

    def close_connections(self) -> None:
        """Close all connections."""
        self._sql.dispose()

    def delete(self) -> None:
        """Delete the database file if it exists."""
        db_file = self._db.replace("sqlite:///", "")
        db_path = Path(db_file)
        db_path.unlink(missing_ok=True)
