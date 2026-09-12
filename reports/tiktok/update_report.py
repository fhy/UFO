#!/usr/bin/env python3
"""Safely replace the published TikTok report after backing up the old copy."""

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
REPORT = BASE / "report.json"
COLLECTION_CACHE = BASE.parents[1] / ".cache" / "tiktok_report_cache.json"
BACKUPS = BASE.parents[1] / ".cache" / "tiktok_report_backups"
SKIPPABLE_STATUSES = {"checked-no-featured-section", "no_featured"}


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def product_key(product: dict[str, Any]) -> str:
    """Prefer a real product ID, otherwise use stable visible fields."""
    if product.get("id"):
        return f"id:{product['id']}"
    return "name:{}|price:{}".format(
        _normalize(product.get("name")), _normalize(product.get("price"))
    )


def validate_product(product: Any) -> None:
    if not isinstance(product, dict) or not product.get("name"):
        raise ValueError("each product must have a non-empty name")
    status = product.get("status", "checked")
    has_featured = product.get("featured_section") is not None
    if status in SKIPPABLE_STATUSES and has_featured:
        raise ValueError("a no-featured product cannot have featured_section")
    if has_featured and not product.get("featured_count"):
        raise ValueError("a featured product must have featured_count")


def _load(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def update_report(new_report: dict[str, Any]) -> None:
    products = new_report.get("products")
    if not isinstance(products, list) or not products:
        raise ValueError("report must contain a non-empty products array")
    for product in products:
        validate_product(product)

    current = _load(REPORT, {"updated_at": None, "products": [], "notes": []})
    existing = {product_key(p): p for p in current.get("products", [])}
    for product in products:
        existing[product_key(product)] = product
    merged = dict(current)
    merged.update({k: v for k, v in new_report.items() if k != "products"})
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()
    merged["products"] = list(existing.values())

    cache = _load(COLLECTION_CACHE, {"schema_version": 2, "products": {}, "creators": {}})
    cache["schema_version"] = max(cache.get("schema_version", 1), 2)
    cache["updated_at"] = merged["updated_at"]
    cache.setdefault("products", {})
    for product in products:
        cache["products"][product_key(product)] = product
        for video in product.get("videos", []):
            creator = video.get("creator") or {}
            creator_key = creator.get("handle") or creator.get("id") or creator.get("nickname")
            if creator_key:
                cache.setdefault("creators", {})[creator_key] = creator

    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if REPORT.exists():
        shutil.copy2(REPORT, BACKUPS / f"report-{stamp}.json")
    if COLLECTION_CACHE.exists():
        shutil.copy2(COLLECTION_CACHE, BACKUPS / f"cache-{stamp}.json")
    _atomic_write(REPORT, merged)
    _atomic_write(COLLECTION_CACHE, cache)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="JSON file containing one or more product records")
    args = parser.parse_args()

    with args.source.open(encoding="utf-8") as stream:
        new_report = json.load(stream)
    if not isinstance(new_report, dict):
        raise ValueError("source must contain a JSON object")
    update_report(new_report)
    print(f"Backed up previous data and updated {REPORT} and {COLLECTION_CACHE}")


if __name__ == "__main__":
    main()
