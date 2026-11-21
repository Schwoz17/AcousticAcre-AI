"""Tests use their own fake language packs, so the demo setting from .env must not filter them.
Set before app.main reads .env (it only fills in variables that are not already set)."""
import os

os.environ["DEMO_LANGS"] = ""