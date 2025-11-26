DEFAULT_PATHWAY: str = ".zeni/"


def sql_directory(folder_path: str, name: str) -> str:
    return f"sqlite:///{folder_path}/{name}.db"
