"""Separate read-only application resources from private writable user data."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('LINEAGE_DATA_DIR', str(ROOT))).expanduser().resolve()
CONFIG = DATA / 'config.local.json'
RESOURCES = Path(os.environ.get('LINEAGE_RESOURCES_DIR', str(ROOT))).resolve()
PACKAGED = os.environ.get('LINEAGE_PACKAGED') == '1'
HELPERS = RESOURCES / 'Payload/helpers' if PACKAGED else ROOT / '.build'
