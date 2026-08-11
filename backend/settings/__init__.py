import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

ENV = os.environ.get("ENV", "dev").lower()

env_files = {
    "dev": BASE_DIR / ".env.dev",
    "staging": BASE_DIR / ".env.staging",
    "prod": BASE_DIR / ".env.prod",
}

env_file = env_files.get(ENV, env_files["dev"])

load_dotenv(env_file)

print(f"Loading environment: {ENV}")
print(f"Loading env file: {env_file}")

if ENV == "prod":
    from .prod import *
elif ENV == "staging":
    from .staging import *
elif ENV == "dev":
    from .dev import *
else:
    raise ValueError(f"Invalid ENV value: {ENV}")