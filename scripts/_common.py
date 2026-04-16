"""Shared helpers for all pipeline scripts.

Goals:
- One place for HTTP behaviour (User-Agent, retries, polite sleep).
- One place for JSON I/O (UTF-8, indent, sorted keys for reproducibility).
- One place for the Excel loader so column index lookup is consistent.
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

import requests

# ---------------------------------------------------------------------------
# .env loader (no python-dotenv dependency)
# ---------------------------------------------------------------------------

def load_env_file(path: Path | None = None) -> None:
    """Load KEY=value pairs from a .env file into os.environ.

    Already-set environment variables win over the file. Lines starting with
    # are comments. Quotes around values are stripped. Missing file is fine.
    """
    if path is None:
        # Repo root .env
        path = Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# Auto-load on import so any script that uses _common picks up .env values.
load_env_file()

USER_AGENT = (
    "objekt-bestimmung-workshop-2026/1.0 "
    "(Workshop demo, Landessammlungen NOE; contact: christopher.pollin@dhcraft.org)"
)
DEFAULT_TIMEOUT = 30
DEFAULT_SLEEP = 1.0
DEFAULT_RETRIES = 3


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Print to stderr so script stdout stays clean for piping."""
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# JSON I/O
# ---------------------------------------------------------------------------

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

@dataclass
class HttpClient:
    """Polite HTTP client: User-Agent, retries with backoff, sleep between calls."""

    sleep: float = DEFAULT_SLEEP
    retries: int = DEFAULT_RETRIES
    timeout: int = DEFAULT_TIMEOUT

    def __post_init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        self._last_call = 0.0

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.sleep:
            time.sleep(self.sleep - elapsed)

    def get(self, url: str) -> requests.Response:
        last_err: Exception | None = None
        for attempt in range(1, self.retries + 1):
            self._wait()
            try:
                resp = self._session.get(url, timeout=self.timeout)
                self._last_call = time.monotonic()
                if resp.status_code == 200:
                    return resp
                last_err = RuntimeError(f"HTTP {resp.status_code} for {url}")
            except requests.RequestException as e:
                last_err = e
            backoff = 2 ** attempt
            log(f"  retry {attempt}/{self.retries} after {backoff}s: {last_err}")
            time.sleep(backoff)
        raise RuntimeError(f"failed after {self.retries} retries: {url}") from last_err


# ---------------------------------------------------------------------------
# Excel loader
# ---------------------------------------------------------------------------

@dataclass
class ExcelTable:
    header: tuple[str, ...]
    rows: list[tuple[Any, ...]]
    col: dict[str, int]

    def get(self, row: tuple[Any, ...], column: str) -> Any:
        return row[self.col[column]]

    def iter_dicts(self) -> Iterator[dict[str, Any]]:
        for r in self.rows:
            yield {name: r[i] for name, i in self.col.items()}


def load_excel(path: Path) -> ExcelTable:
    """Read the source Excel into a single-pass-friendly structure."""
    import openpyxl  # imported lazily so requirements stay optional for non-Excel scripts

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    iterator = ws.iter_rows(values_only=True)
    header = tuple(next(iterator))
    rows = [r for r in iterator if any(c is not None for c in r)]
    col = {name: i for i, name in enumerate(header)}
    return ExcelTable(header=header, rows=rows, col=col)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def write_report(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip() + "\n")


# ---------------------------------------------------------------------------
# Thesaurus utilities
# ---------------------------------------------------------------------------

def top_id_of(cn: str) -> str:
    """First three CN segments form the top-area code, e.g. AUT.AAW.AAH."""
    return ".".join(cn.split(".")[:3])


# ---------------------------------------------------------------------------
# Gemini call with retry
# ---------------------------------------------------------------------------

@dataclass
class GeminiCallResult:
    payload: Any
    tokens_input: int
    tokens_output: int
    latency_ms: int


def gemini_generate_json(
    model,
    contents,
    schema: dict,
    *,
    max_retries: int = 3,
    temperature: float = 0.2,
    label: str = "gemini",
) -> GeminiCallResult:
    """Run a Gemini generate_content call with JSON response schema and retries.

    Shared between _gemini_client.py (workflows A/B) and 07_correct_sample.py
    (workflow C, Korrektur). Returns parsed JSON plus token usage and latency.
    """
    import google.generativeai as genai  # imported here so _common stays usable without the SDK
    import json as _json

    config = genai.types.GenerationConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=temperature,
    )

    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        started = time.monotonic()
        try:
            resp = model.generate_content(contents, generation_config=config)
            latency = int((time.monotonic() - started) * 1000)
            payload = _json.loads(resp.text)
            usage = getattr(resp, "usage_metadata", None)
            return GeminiCallResult(
                payload=payload,
                tokens_input=getattr(usage, "prompt_token_count", 0) or 0,
                tokens_output=getattr(usage, "candidates_token_count", 0) or 0,
                latency_ms=latency,
            )
        except Exception as e:
            last_err = e
            wait = 2 ** attempt
            log(f"  {label} retry {attempt}/{max_retries} after {wait}s: {e}")
            time.sleep(wait)
    raise RuntimeError(f"{label} call failed after {max_retries} retries") from last_err
