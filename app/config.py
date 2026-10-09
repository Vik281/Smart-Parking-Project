import os

# Read from the environment so tests and production can point at a different database.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./parkshare.db")
