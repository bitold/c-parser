from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from config.env import parse_optional_path_env, require_env
from config.models.Neo4jConfig import Neo4jConfig


def Neo4jConfigMapper(
    env_file: str | Path | None = ".env",
    *,
    override: bool = False,
) -> Neo4jConfig:
    """Read Neo4j connection fields from a `.env` file / process environment."""
    if env_file is not None:
        path = Path(env_file)
        if path.is_file():
            load_dotenv(path, override=override)
        elif env_file != ".env":
            raise FileNotFoundError(f"Env file not found: {path}")
        else:
            load_dotenv(override=override)

    return Neo4jConfig(
        uri=require_env("NEO4J_URI"),
        username=require_env("NEO4J_USERNAME"),
        password=require_env("NEO4J_PASSWORD"),
        database=require_env("NEO4J_DATABASE"), 
    )
