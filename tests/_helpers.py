import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "ziddi-af" / "scripts"
sys.path.insert(0, str(SCRIPTS))
EXAMPLE_CONFIG = ROOT / "examples" / "ziddi.example.config.json"


def temp_home():
    d = tempfile.mkdtemp(prefix="ziddi-test-")
    os.environ["ZIDDI_HOME"] = d
    os.environ.pop("ZIDDI_ATTEMPTS", None)
    os.environ.pop("ZIDDI_CONFIG", None)
    return Path(d)


def load_example():
    from ziddi_lib import config as cfgmod
    return cfgmod.load(str(EXAMPLE_CONFIG))
