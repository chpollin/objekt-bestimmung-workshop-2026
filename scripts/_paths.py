"""Central path constants for the pipeline.

All scripts import from here so paths are defined exactly once.
"""
from pathlib import Path

# Repo root = parent of scripts/
ROOT = Path(__file__).resolve().parent.parent

# Source data
SOURCE_XLSX = ROOT / "data" / "Trainingsobjekte_LandNOE_VK.xlsx"

# JSON outputs (committed)
DATA_JSON = ROOT / "data" / "json"
THESAURUS_JSON = DATA_JSON / "thesaurus.json"
THESAURUS_FLAT_JSON = DATA_JSON / "thesaurus_flat.json"
OBJECTS_JSON = DATA_JSON / "objects.json"
ORIGINALS_JSON = DATA_JSON / "originals.json"
AI_BLIND_JSON = DATA_JSON / "ai_blind.json"
AI_ENRICHED_JSON = DATA_JSON / "ai_enriched.json"
EDITS_JSON = DATA_JSON / "edits.json"

# Image assets (committed)
IMAGES_DIR = ROOT / "assets" / "img"

# Pipeline working files
SCRIPTS = ROOT / "scripts"
CACHE_DIR = SCRIPTS / "cache"
TOP_NAMES_CACHE = CACHE_DIR / "top_names.json"
ORIGINALS_CACHE_DIR = CACHE_DIR / "originals"
PREVIEW_HTML = SCRIPTS / "preview.html"

# Reports
SELECTION_REPORT = SCRIPTS / "selection_report.txt"
SCRAPE_REPORT = SCRIPTS / "scrape_report.txt"
DOWNLOAD_REPORT = SCRIPTS / "download_report.txt"

# Prompts (M2)
PROMPTS_DIR = SCRIPTS / "prompts"
SYSTEM_BLIND_TXT = PROMPTS_DIR / "system_blind.txt"
SYSTEM_ENRICHED_TXT = PROMPTS_DIR / "system_enriched.txt"
SYSTEM_JUDGE_TXT = PROMPTS_DIR / "system_judge.txt"
FEW_SHOT_JSON = PROMPTS_DIR / "few_shot_examples.json"

# Judge outputs (M2)
AI_JUDGE_JSON = DATA_JSON / "ai_judge.json"
AI_JUDGE_SAMPLE = DATA_JSON / "ai_judge_sample.json"

# Online collection
ONLINE_BASE = "https://online.landessammlungen-noe.at"


def ensure_dirs() -> None:
    """Create all output directories that scripts write to."""
    for d in (DATA_JSON, IMAGES_DIR, CACHE_DIR, ORIGINALS_CACHE_DIR, PROMPTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
