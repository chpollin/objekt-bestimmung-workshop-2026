"""Download object images from the online collection and resize them locally.

For each object in objects.json:
- Skip if assets/img/{object_id}.jpg already exists (resume-friendly).
- Fetch URL_Foto with polite headers and retries.
- Resize so the long edge is at most --max-edge pixels (default 1024). The
  optimal value gets verified in M2 with an A/B test against Gemini.
- Save as JPEG, quality 85, RGB.

Output:
- assets/img/{object_id}.jpg
- scripts/download_report.txt
"""
from __future__ import annotations

import argparse
import io
from pathlib import Path

from _common import HttpClient, log, read_json, write_report
from _paths import (
    DOWNLOAD_REPORT,
    IMAGES_DIR,
    OBJECTS_JSON,
    ensure_dirs,
)

DEFAULT_MAX_EDGE = 1024
DEFAULT_QUALITY = 85


def resize_to(image_bytes: bytes, max_edge: int, quality: int) -> bytes:
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    long_edge = max(w, h)
    if long_edge > max_edge:
        scale = max_edge / long_edge
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-edge", type=int, default=DEFAULT_MAX_EDGE)
    parser.add_argument("--quality", type=int, default=DEFAULT_QUALITY)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the local file already exists.",
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    ensure_dirs()
    objects = read_json(OBJECTS_JSON)
    if objects is None:
        raise SystemExit("objects.json missing — run 02_select_objects.py first")

    if args.limit:
        objects = objects[: args.limit]

    http = HttpClient(sleep=0.5)
    downloaded = 0
    skipped = 0
    errors: list[tuple[int, str]] = []
    total_bytes = 0

    log(f"downloading up to {len(objects)} images to {IMAGES_DIR}")
    for i, obj in enumerate(objects, start=1):
        oid = obj["object_id"]
        url = obj.get("url_image_remote")
        if not url:
            errors.append((oid, "no url_image_remote"))
            continue
        target: Path = IMAGES_DIR / f"{oid}.jpg"
        if target.exists() and not args.force:
            skipped += 1
            total_bytes += target.stat().st_size
            continue
        try:
            resp = http.get(url)
            data = resize_to(resp.content, args.max_edge, args.quality)
            target.write_bytes(data)
            downloaded += 1
            total_bytes += len(data)
        except Exception as e:
            errors.append((oid, str(e)))
            log(f"  {oid} -> {e}")
            continue
        if i % 25 == 0:
            log(f"  progress: {i}/{len(objects)}")

    report: list[str] = []
    report.append(f"Downloaded: {downloaded}")
    report.append(f"Skipped (already present): {skipped}")
    report.append(f"Errors: {len(errors)}")
    report.append(f"Max edge: {args.max_edge}px  quality: {args.quality}")
    report.append(f"Total bytes on disk: {total_bytes:,}")
    if errors:
        report.append("")
        report.append("Failures:")
        for oid, msg in errors:
            report.append(f"  {oid}: {msg}")
    write_report(DOWNLOAD_REPORT, report)
    log(f"wrote {DOWNLOAD_REPORT}")
    for line in report[:6]:
        log("  " + line)


if __name__ == "__main__":
    main()
