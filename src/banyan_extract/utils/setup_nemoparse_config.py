import os

from dotenv import dotenv_values


def get_nemoparse_config(config_file: str | None = ".env") -> dict[str, str | None]:
    """Read endpoint settings from a dotenv file with environment fallbacks."""
    values = dotenv_values(config_file) if config_file and os.path.exists(config_file) else {}
    for name in ("NEMOPARSE_ENDPOINT", "NEMOPARSE_MODEL", "NEMOPARSE_MODEL_VERSION"):
        values[name] = values.get(name) or os.getenv(name)
    values["NEMOPARSE_API_KEY"] = os.getenv("NEMOPARSE_API_KEY") or values.get("NEMOPARSE_API_KEY")
    return values
