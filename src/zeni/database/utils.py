from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from .repos import AccountRepo, TransactionRepo


@dataclass
class Workspace:
    """Dataclass to handle SQL Alchemy sessions.

    Stores access to the session itself as well as repository classes that
    require a session to be instanciated.

    Given a SQL Alchemy `Engine` object, this workspace should be used as a context
    nanager:
    ```python
    with Workspace.open(Engine) as ws:
       ws.session.scalar(...)
       ...
    ```
    """

    session: Session
    accounts: AccountRepo
    transactions: TransactionRepo

    @classmethod
    @contextmanager
    def open(cls, engine: Engine) -> Generator[Workspace]:
        with Session(engine) as session, session.begin():
            yield cls(session, AccountRepo(session), TransactionRepo(session))


def get_project_root() -> Path:
    """Get the project root directory (where .git or pyproject.toml exists)."""
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


DEFAULT_PATHWAY: Path = get_project_root() / ".zeni"


def sql_directory(folder_path: str, name: str) -> str:
    return f"sqlite:///{folder_path}/{name}.db"


def list_databases(folder_path: str = DEFAULT_PATHWAY) -> list[str]:
    """List all database names in the specified folder.

    Args:
        folder_path: Path to folder containing databases (default: .zeni/)

    Returns:
        List of database names (without .db extension)
    """
    db_path = Path(folder_path)
    if not db_path.exists():
        return []

    return [db.stem for db in db_path.glob("*.db")]
