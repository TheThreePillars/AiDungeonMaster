"""Quick content audit to verify PF1e coverage for level 12."""

from __future__ import annotations

import json
from pathlib import Path

SRD_DIR = Path("data/srd")
CORE_CLASSES = ["bard", "cleric", "druid", "paladin", "ranger", "sorcerer", "wizard"]


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def audit_spells() -> None:
    data = load_json(SRD_DIR / "spells.json")
    spells = data.get("spells", []) + data.get("cantrips", [])
    max_level = {cls: 0 for cls in CORE_CLASSES}
    for spell in spells:
        levels = spell.get("level", {})
        if not isinstance(levels, dict):
            continue
        for cls, lvl in levels.items():
            cls = cls.lower()
            if cls in max_level:
                max_level[cls] = max(max_level[cls], int(lvl))
    print("Spells:", len(spells))
    print("Max spell level by class:", max_level)


def audit_classes() -> None:
    data = load_json(SRD_DIR / "classes.json")
    classes = data.get("classes", [])
    for cls in classes:
        levels = [f.get("level") for f in cls.get("features", []) if isinstance(f.get("level"), int)]
        max_level = max(levels) if levels else 0
        print(f"Class {cls.get('name','?')}: max feature level {max_level}")


def audit_simple_list(filename: str, label: str, key: str) -> None:
    data = load_json(SRD_DIR / filename)
    items = data.get(key, [])
    print(f"{label}: {len(items)}")


def main() -> None:
    print("=== SRD Content Audit ===")
    audit_spells()
    audit_classes()
    audit_simple_list("feats.json", "Feats", "feats")
    audit_simple_list("magic_items.json", "Magic items", "items")
    audit_simple_list("artifacts.json", "Artifacts", "artifacts")


if __name__ == "__main__":
    main()
