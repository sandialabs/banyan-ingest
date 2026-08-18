import os

from dotenv import load_dotenv, dotenv_values


def get_nemoparse_config(config_file: str | None = ".env"):
    if os.path.exists(config_file):
        config_values = dotenv_values(config_file)
    else:
        config_values = dict()
        config_values["NEMOPARSE_ENDPOINT"] = os.getenv("NEMOPARSE_ENDPOINT", None)
        config_values["NEMOPARSE_MODEL"] = os.getenv("NEMOPARSE_MODEL", None)
        config_values["NEMOPARSE_MODEL_VERSION"] = os.getenv("NEMOPARSE_MODEL_VERSION", None)

    return config_values
