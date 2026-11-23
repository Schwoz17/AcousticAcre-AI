"""Tests use their own settings, so demo settings from .env must not affect them.
Set before app.main reads .env (it only fills in variables that are not already set)."""
import os

os.environ["DEMO_LANGS"] = ""
os.environ["ALLOW_UNREVIEWED"] = "0"   # tests expect English only, like a fresh install
