"""Scrape PF1e SRD content from d20pfsrd and store as local JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

USER_AGENT = "Mozilla/5.0 (Codex SRD Scraper)"

CORE_CLASSES = {
    "bard",
    "cleric",
    "druid",
    "paladin",
    "ranger",
    "sorcerer",
    "wizard",
}

CLASS_URLS = {
    "Fighter": "https://www.d20pfsrd.com/classes/core-classes/fighter/",
    "Rogue": "https://www.d20pfsrd.com/classes/core-classes/rogue/",
    "Wizard": "https://www.d20pfsrd.com/classes/core-classes/wizard/",
    "Cleric": "https://www.d20pfsrd.com/classes/core-classes/cleric/",
    "Barbarian": "https://www.d20pfsrd.com/classes/core-classes/barbarian/",
    "Bard": "https://www.d20pfsrd.com/classes/core-classes/bard/",
    "Paladin": "https://www.d20pfsrd.com/classes/core-classes/paladin/",
    "Ranger": "https://www.d20pfsrd.com/classes/core-classes/ranger/",
    "Sorcerer": "https://www.d20pfsrd.com/classes/core-classes/sorcerer/",
    "Monk": "https://www.d20pfsrd.com/classes/core-classes/monk/",
    "Druid": "https://www.d20pfsrd.com/classes/core-classes/druid/",
}

DAMAGE_TYPES = [
    "acid",
    "cold",
    "electricity",
    "fire",
    "force",
    "negative energy",
    "positive energy",
    "sonic",
]

SPELL_LIST_PAGES = {
    "spells-a-d": "https://www.d20pfsrd.com/magic/all-spells/spells-a-d/",
    "spells-e-h": "https://www.d20pfsrd.com/magic/all-spells/spells-e-h/",
    "spells-i-l": "https://www.d20pfsrd.com/magic/all-spells/spells-i-l/",
    "spells-m-p": "https://www.d20pfsrd.com/magic/all-spells/spells-m-p/",
    "spells-q-t": "https://www.d20pfsrd.com/magic/all-spells/spells-q-t/",
    "spells-u-z": "https://www.d20pfsrd.com/magic/all-spells/spells-u-z/",
}

FEAT_LIST_PAGES = {
    "combat-feats": "https://www.d20pfsrd.com/feats/combat-feats/",
    "general-feats": "https://www.d20pfsrd.com/feats/general-feats/",
    "item-creation-feats": "https://www.d20pfsrd.com/feats/item-creation-feats/",
    "metamagic-feats": "https://www.d20pfsrd.com/feats/metamagic-feats/",
    "teamwork-feats": "https://www.d20pfsrd.com/feats/teamwork-feats/",
    "critical-feats": "https://www.d20pfsrd.com/feats/combat-feats/critical-feats/",
    "performance-feats": "https://www.d20pfsrd.com/feats/performance-feats/",
    "racial-feats": "https://www.d20pfsrd.com/feats/racial-feats/",
    "skill-feats": "https://www.d20pfsrd.com/feats/skill-feats/",
    "style-feats": "https://www.d20pfsrd.com/feats/style-feats/",
}

MAGIC_ITEM_CATEGORIES = {
    "wondrous": "https://www.d20pfsrd.com/magic-items/wondrous-items/",
    "weapons": "https://www.d20pfsrd.com/magic-items/magic-weapons/",
    "armor": "https://www.d20pfsrd.com/magic-items/magic-armor/",
    "rings": "https://www.d20pfsrd.com/magic-items/rings/",
    "rods": "https://www.d20pfsrd.com/magic-items/rods/",
    "staves": "https://www.d20pfsrd.com/magic-items/staves/",
    "wands": "https://www.d20pfsrd.com/magic-items/wands/",
    "scrolls": "https://www.d20pfsrd.com/magic-items/scrolls/",
    "potions": "https://www.d20pfsrd.com/magic-items/potions/",
}

MAGIC_ITEM_PREFIXES = [
    "a-b",
    "c-d",
    "e-g",
    "h-j",
    "k-m",
    "n-p",
    "q-s",
    "t-v",
    "w-z",
]

ARTIFACT_CATEGORIES = {
    "minor-artifacts": "https://www.d20pfsrd.com/magic-items/artifacts/minor-artifacts/",
    "major-artifacts": "https://www.d20pfsrd.com/magic-items/artifacts/major-artifacts/",
}

WEAPON_CATEGORY_MAP = {
    "(Simple)Unarmed Attacks": "simple_melee",
    "(Simple)Light Melee Weapons": "simple_melee",
    "(Simple)One-Handed Melee Weapons": "simple_melee",
    "(Simple)Two-Handed Melee Weapons": "simple_melee",
    "(Simple)Ranged Weapons": "simple_ranged",
    "(Simple)Ammunition": "simple_ammunition",
    "(Martial)Light Melee Weapons": "martial_melee",
    "(Martial)One-Handed Melee Weapons": "martial_melee",
    "(Martial)Two-Handed Melee Weapons": "martial_melee",
    "(Martial)Ranged Weapons": "martial_ranged",
    "(Martial)Ammunition": "martial_ammunition",
    "(Exotic)Light Melee Weapons": "exotic_melee",
    "(Exotic)One-Handed Melee Weapons": "exotic_melee",
    "(Exotic)Two-Handed Melee Weapons": "exotic_melee",
    "(Exotic)Ranged Weapons": "exotic_ranged",
    "(Exotic)Ammunition": "exotic_ammunition",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def get_text(self) -> str:
        return "".join(self.parts)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return unescape(parser.get_text())


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_tags(html: str) -> str:
    html = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?>.*?</style>", "", html, flags=re.S | re.I)
    return html_to_text(html)


def parse_number(text: str) -> float | int | None:
    cleaned = normalize_spaces(strip_tags(text)).lower()
    if cleaned in ("—", "-", ""):
        return None
    cleaned = cleaned.replace("gp", "").replace("lbs.", "").replace("lb.", "").replace("ft.", "")
    cleaned = cleaned.replace(",", "").replace("+", "")
    match = re.search(r"-?\d+(\.\d+)?", cleaned)
    if not match:
        return None
    value = float(match.group(0))
    return int(value) if value.is_integer() else value


def parse_percentage(text: str) -> int | None:
    cleaned = normalize_spaces(strip_tags(text)).replace("%", "")
    match = re.search(r"-?\d+", cleaned)
    return int(match.group(0)) if match else None


def parse_weapon_special(text: str) -> list[str]:
    cleaned = normalize_spaces(strip_tags(text))
    if not cleaned or cleaned == "—":
        return []
    return [part.strip().lower() for part in cleaned.split(",") if part.strip()]


def parse_table_rows(table_html: str) -> list[list[str]]:
    rows = []
    for row in re.findall(r"<tr>(.*?)</tr>", table_html, flags=re.I | re.S):
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, flags=re.I | re.S)
        rows.append(cells)
    return rows


def prefix_matches(name: str, prefixes: list[str] | None) -> bool:
    if not prefixes:
        return True
    match = re.search(r"[a-z]", name.lower())
    if not match:
        return False
    letter = match.group(0)
    for prefix in prefixes:
        if "-" in prefix:
            start, end = prefix.split("-", 1)
            if start <= letter <= end:
                return True
        elif letter == prefix:
            return True
    return False


def slug_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def fetch_url(url: str, cache_dir: Path, delay: float, force: bool) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = slug_hash(url)
    cache_path = cache_dir / f"{cache_key}.html"
    if cache_path.exists() and not force:
        return cache_path.read_text(encoding="utf-8")
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req) as response:
        data = response.read().decode("utf-8", errors="ignore")
    cache_path.write_text(data, encoding="utf-8")
    if delay > 0:
        time.sleep(delay)
    return data


def extract_links(html: str, base_url: str) -> list[str]:
    links = re.findall(r'href="([^"]+)"', html, flags=re.I)
    resolved = []
    for link in links:
        if link.startswith("#") or link.startswith("mailto:"):
            continue
        resolved.append(urljoin(base_url, link))
    return resolved


def unique_links(links: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for link in links:
        if link in seen:
            continue
        seen.add(link)
        out.append(link)
    return out


def is_spell_link(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if "/magic/all-spells/" not in path:
        return False
    if path.endswith("/magic/all-spells/"):
        return False
    if "/spells-" in path:
        return False
    return path.count("/") >= 5


def is_feat_link(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if "/feats/" not in path:
        return False
    if path.endswith("/feats/"):
        return False
    if "feats-db" in path or "feat-tree" in path:
        return False
    if path.endswith("/combat-feats/") or path.endswith("/general-feats/"):
        return False
    if path.count("/") < 4:
        return False
    return True


def is_item_link(url: str, prefix: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if prefix not in path:
        return False
    if path.endswith(prefix) or path.endswith(prefix + "/"):
        return False
    if path.rstrip("/").endswith("/minor-artifacts") or path.rstrip("/").endswith("/major-artifacts"):
        return False
    return True


def extract_block(html: str, label: str) -> str | None:
    pattern = rf"<p><b>{re.escape(label)}</b>.*?</p>"
    match = re.search(pattern, html, flags=re.I | re.S)
    return match.group(0) if match else None


def extract_divider_section(html: str, label: str) -> str:
    pattern = rf"<p class=\"divider\">{re.escape(label)}</p>(.*?)(<p class=\"divider\">|<div class=\"section|</div>)"
    match = re.search(pattern, html, flags=re.I | re.S)
    return match.group(1) if match else ""


def parse_labeled_lines(html: str) -> dict[str, str]:
    text = html.replace("<br />", "\n").replace("<br/>", "\n")
    text = strip_tags(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result: dict[str, str] = {}
    for line in lines:
        if ":" in line:
            label, value = line.split(":", 1)
            result[label.strip()] = value.strip()
            continue
        for label in ("Range", "Target", "Effect", "Duration", "Saving Throw", "Spell Resistance"):
            if line.lower().startswith(label.lower()):
                result[label] = line[len(label):].strip()
                break
    return result


def parse_spell_levels(text: str) -> dict[str, int]:
    levels: dict[str, int] = {}
    parts = [p.strip() for p in text.split(",") if p.strip()]
    for part in parts:
        if part.lower().startswith("level"):
            part = part[len("level"):].strip()
        if part.lower().startswith("spell"):
            continue
        match = re.search(r"([a-zA-Z/ ]+)\s+(\d+)", part)
        if not match:
            continue
        classes = match.group(1).strip().lower().replace("sorcerer/wizard", "sorcerer wizard")
        level = int(match.group(2))
        for cls in re.split(r"[ /]+", classes):
            cls = cls.strip()
            if not cls:
                continue
            if cls in CORE_CLASSES:
                levels[cls] = min(levels.get(cls, level), level)
    return levels


def infer_damage(description: str) -> tuple[str | None, str | None]:
    text = description.lower()
    match = re.search(r"(\\d+d\\d+(?:\\s*[+-]\\s*\\d+)?)\\s+points? of ([a-z ]+) damage", text)
    if not match:
        return None, None
    dice = match.group(1).replace(" ", "")
    damage_phrase = match.group(2)
    damage_type = None
    for dtype in DAMAGE_TYPES:
        if dtype in damage_phrase:
            damage_type = dtype
            break
    return dice, damage_type


def infer_heal(description: str) -> str | None:
    text = description.lower()
    match = re.search(r"(cure|cures|heal|heals|restores)\\s+(\\d+d\\d+(?:\\s*[+-]\\s*\\d+)?)", text)
    if not match:
        return None
    return match.group(2).replace(" ", "")


def parse_spell_page(html: str) -> dict[str, object] | None:
    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
    name = normalize_spaces(strip_tags(title_match.group(1))).replace("– d20PFSRD", "").strip() if title_match else ""
    school_block = extract_block(html, "School")
    if not school_block:
        return None
    school_text = strip_tags(school_block)
    school_match = re.search(r"School\s+([^;]+)", school_text, flags=re.I)
    school_raw = school_match.group(1) if school_match else ""
    school_main = school_raw.split("(")[0].strip()
    subschool = ""
    if "(" in school_raw and ")" in school_raw:
        subschool = school_raw[school_raw.find("(") + 1 : school_raw.find(")")].strip()
    level_match = re.search(r"Level\s+(.+)", school_text, flags=re.I)
    level_text = level_match.group(1) if level_match else ""
    level_text = level_text.split(";")[0]
    levels = parse_spell_levels(level_text)
    if not levels:
        return None

    casting_block = extract_block(html, "Casting Time") or ""
    casting_fields = parse_labeled_lines(casting_block)
    effect_block = extract_block(html, "Range") or ""
    effect_fields = parse_labeled_lines(effect_block)
    description_html = extract_divider_section(html, "DESCRIPTION")
    description_text = normalize_spaces(strip_tags(description_html))
    damage_dice, damage_type = infer_damage(description_text)
    heal_dice = infer_heal(description_text)

    components = []
    if "Components" in casting_fields:
        components = [c.strip() for c in casting_fields["Components"].split(",") if c.strip()]

    return {
        "name": name,
        "school": school_main.title(),
        "subschool": subschool,
        "level": levels,
        "casting_time": casting_fields.get("Casting Time", ""),
        "components": components,
        "range": effect_fields.get("Range", ""),
        "target": effect_fields.get("Target", effect_fields.get("Effect", "")),
        "duration": effect_fields.get("Duration", ""),
        "saving_throw": effect_fields.get("Saving Throw", ""),
        "spell_resistance": effect_fields.get("Spell Resistance", ""),
        "description": description_text,
        "damage_dice": damage_dice,
        "damage_type": damage_type,
        "heal_dice": heal_dice,
    }


def parse_feat_page(html: str) -> dict[str, str] | None:
    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
    name = normalize_spaces(strip_tags(title_match.group(1))).replace("– d20PFSRD", "").strip() if title_match else ""
    prereq_block = extract_block(html, "Prerequisites")
    benefit_block = extract_block(html, "Benefit")
    if not benefit_block:
        return None
    prereq_text = normalize_spaces(strip_tags(prereq_block)) if prereq_block else ""
    benefit_text = normalize_spaces(strip_tags(benefit_block))
    normal_block = extract_block(html, "Normal")
    special_block = extract_block(html, "Special")
    return {
        "name": name,
        "prerequisites": prereq_text.replace("Prerequisites", "").strip(" :"),
        "benefit": benefit_text.replace("Benefit", "").strip(" :"),
        "normal": normalize_spaces(strip_tags(normal_block)).replace("Normal", "").strip(" :") if normal_block else "",
        "special": normalize_spaces(strip_tags(special_block)).replace("Special", "").strip(" :") if special_block else "",
    }


def parse_item_page(html: str) -> dict[str, str] | None:
    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
    name = normalize_spaces(strip_tags(title_match.group(1))).replace("– d20PFSRD", "").strip() if title_match else ""
    aura_block = extract_block(html, "Aura")
    if not aura_block:
        return None
    aura_text = normalize_spaces(strip_tags(aura_block))
    fields = {}
    for label in ("Aura", "CL", "Slot", "Price", "Weight"):
        match = re.search(rf"{label}\s+([^;]+)", aura_text, flags=re.I)
        if match:
            fields[label.lower()] = match.group(1).strip()
    description_html = extract_divider_section(html, "DESCRIPTION")
    description_text = normalize_spaces(strip_tags(description_html))
    return {
        "name": name,
        "aura": fields.get("aura", ""),
        "cl": fields.get("cl", ""),
        "slot": fields.get("slot", ""),
        "price": fields.get("price", ""),
        "weight": fields.get("weight", ""),
        "description": description_text,
    }


def parse_magic_table_items(html: str, item_type: str, prefixes: list[str] | None) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for table in re.findall(r"<table.*?</table>", html, flags=re.I | re.S):
        rows = parse_table_rows(table)
        if not rows:
            continue
        header_row = None
        headers: list[str] = []
        for row in rows:
            candidate = [normalize_spaces(strip_tags(h)).lower() for h in row]
            if any("price" in h for h in candidate):
                header_row = row
                headers = candidate
                break
        if not headers:
            continue
        name_idx = None
        for i, head in enumerate(headers):
            if head in ("item", item_type) or item_type.rstrip("s") in head:
                name_idx = i
                break
            if item_type in ("armor", "weapons") and head in ("armor", "weapon", "shield"):
                name_idx = i
                break
        if name_idx is None:
            continue
        price_idx = None
        for i, head in enumerate(headers):
            if "price" in head:
                price_idx = i
                break
        if price_idx is None:
            continue
        start_index = rows.index(header_row) + 1 if header_row in rows else 1
        for row in rows[start_index:]:
            if len(row) <= max(name_idx, price_idx):
                continue
            name = normalize_spaces(strip_tags(row[name_idx])).replace("*", "").strip()
            if not name or name.lower().startswith("special"):
                continue
            if not prefix_matches(name, prefixes):
                continue
            price = parse_number(row[price_idx]) or 0
            items.append(
                {
                    "name": name,
                    "price": price,
                }
            )
    return items


def extract_anchor_description(html: str, anchor_name: str) -> str:
    anchor_match = re.search(
        rf"(name|id)=\"{re.escape(anchor_name)}\"",
        html,
        flags=re.I,
    )
    if not anchor_match:
        return ""
    start = anchor_match.end()
    end_match = re.search(
        r"<h[1-4][^>]*>|<p class=\"divider\">|<div class=\"section",
        html[start:],
        flags=re.I,
    )
    end = start + end_match.start() if end_match else len(html)
    chunk = html[start:end]
    paragraphs = re.findall(r"<p[^>]*>.*?</p>", chunk, flags=re.I | re.S)
    text_parts = []
    for para in paragraphs:
        text = normalize_spaces(strip_tags(para))
        if not text or text.lower().startswith("source"):
            continue
        text_parts.append(text)
        if len(text_parts) >= 3:
            break
    return " ".join(text_parts).strip()


def parse_class_features(html: str) -> list[dict[str, object]]:
    table_match = None
    for match in re.finditer(r"<table.*?</table>", html, flags=re.I | re.S):
        chunk = match.group(0)
        if "Special" in chunk and "Level" in chunk:
            table_match = chunk
            break
    if not table_match:
        return []

    rows = re.findall(r"<tr>(.*?)</tr>", table_match, flags=re.I | re.S)
    features: list[dict[str, object]] = []
    for row in rows[1:]:
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, flags=re.I | re.S)
        if len(cells) < 6:
            continue
        level_text = normalize_spaces(strip_tags(cells[0]))
        level_match = re.match(r"(\d+)", level_text)
        if not level_match:
            continue
        level = int(level_match.group(1))
        special_html = cells[-1]
        special_text = normalize_spaces(strip_tags(special_html))
        if not special_text or special_text == "—":
            continue
        anchors = re.findall(r"<a[^>]*href=\"#([^\"]+)\"[^>]*>(.*?)</a>", special_html, flags=re.I | re.S)
        anchor_map = {
            normalize_spaces(strip_tags(text)).lower(): target
            for target, text in anchors
        }
        segments = [s.strip() for s in special_text.split(",") if s.strip()]
        for segment in segments:
            segment_lower = segment.lower()
            anchor_key = ""
            for candidate in anchor_map:
                if candidate and candidate in segment_lower and len(candidate) > len(anchor_key):
                    anchor_key = candidate
            description = ""
            if anchor_key:
                description = extract_anchor_description(html, anchor_map[anchor_key])
            if not description:
                description = "See d20pfsrd for details."
            features.append(
                {
                    "level": level,
                    "name": segment,
                    "description": description,
                }
            )
    return features


def scrape_spells(
    cache_dir: Path,
    output_dir: Path,
    delay: float,
    force: bool,
    limit: int | None,
    pages: list[str] | None,
) -> None:
    index_url = "https://www.d20pfsrd.com/magic/all-spells/"
    index_html = fetch_url(index_url, cache_dir, delay, force)
    index_links = extract_links(index_html, index_url)
    list_pages = [link for link in index_links if "all-spells/spells-" in link.lower()]
    list_pages = unique_links(list_pages)
    if pages:
        list_pages = [SPELL_LIST_PAGES[p] for p in pages if p in SPELL_LIST_PAGES]
        if not list_pages:
            raise RuntimeError("No valid spell pages selected.")

    spell_links: list[str] = []
    for page in list_pages:
        page_html = fetch_url(page, cache_dir, delay, force)
        spell_links.extend([l for l in extract_links(page_html, page) if is_spell_link(l)])
    spell_links = unique_links(spell_links)
    if limit:
        spell_links = spell_links[:limit]

    spells = []
    for link in spell_links:
        html = fetch_url(link, cache_dir, delay, force)
        parsed = parse_spell_page(html)
        if parsed:
            spells.append(parsed)

    existing = {}
    spells_path = output_dir / "spells.json"
    if spells_path.exists():
        try:
            existing = json.loads(spells_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}

    combined = []
    combined.extend(existing.get("cantrips", []))
    combined.extend(existing.get("spells", []))
    combined.extend(spells)

    merged: dict[str, dict[str, object]] = {}
    for entry in combined:
        name = entry.get("name", "").strip()
        if not name:
            continue
        merged[name.lower()] = entry

    merged_list = list(merged.values())
    cantrips = [s for s in merged_list if any(level == 0 for level in s["level"].values())]
    leveled = [s for s in merged_list if s not in cantrips]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "spells.json").write_text(
        json.dumps({"spells": leveled, "cantrips": cantrips}, indent=2),
        encoding="utf-8",
    )


def scrape_feats(
    cache_dir: Path,
    output_dir: Path,
    delay: float,
    force: bool,
    limit: int | None,
    pages: list[str] | None,
) -> None:
    index_url = "https://www.d20pfsrd.com/feats/"
    index_html = fetch_url(index_url, cache_dir, delay, force)
    index_links = extract_links(index_html, index_url)
    if pages:
        list_pages = [FEAT_LIST_PAGES[p] for p in pages if p in FEAT_LIST_PAGES]
        if not list_pages:
            raise RuntimeError("No valid feat pages selected.")
        index_links = []
        for page in list_pages:
            try:
                page_html = fetch_url(page, cache_dir, delay, force)
            except Exception:
                continue
            index_links.extend(extract_links(page_html, page))
    feat_links = [link for link in index_links if is_feat_link(link)]
    feat_links = unique_links(feat_links)
    if limit:
        feat_links = feat_links[:limit]

    feats = []
    for link in feat_links:
        try:
            html = fetch_url(link, cache_dir, delay, force)
        except Exception:
            continue
        parsed = parse_feat_page(html)
        if parsed:
            feats.append(parsed)

    existing = {}
    feats_path = output_dir / "feats.json"
    if feats_path.exists():
        try:
            existing = json.loads(feats_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}

    combined = []
    combined.extend(existing.get("feats", []))
    combined.extend(feats)

    merged: dict[str, dict[str, str]] = {}
    for entry in combined:
        name = entry.get("name", "").strip()
        if not name:
            continue
        merged[name.lower()] = entry

    feats = list(merged.values())

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "feats.json").write_text(
        json.dumps({"feats": feats}, indent=2),
        encoding="utf-8",
    )


def scrape_items_from_index(
    index_url: str,
    cache_dir: Path,
    delay: float,
    force: bool,
    limit: int | None,
    prefixes: list[str] | None,
) -> list[dict[str, str]]:
    index_html = fetch_url(index_url, cache_dir, delay, force)
    index_links = extract_links(index_html, index_url)
    prefix = urlparse(index_url).path.lower()
    item_links = [link for link in index_links if is_item_link(link, prefix)]
    if prefixes:
        filtered = []
        for link in item_links:
            path = urlparse(link).path.lower()
            if any(f"/{p}/" in path for p in prefixes):
                filtered.append(link)
        item_links = filtered
    item_links = unique_links(item_links)
    if limit:
        item_links = item_links[:limit]

    items = []
    for link in item_links:
        try:
            html = fetch_url(link, cache_dir, delay, force)
        except Exception:
            continue
        parsed = parse_item_page(html)
        if parsed:
            parsed["source_url"] = link
            items.append(parsed)
    return items


def scrape_magic_items(
    cache_dir: Path,
    output_dir: Path,
    delay: float,
    force: bool,
    limit: int | None,
    categories: list[str] | None,
    prefixes: list[str] | None,
) -> None:
    categories_map = MAGIC_ITEM_CATEGORIES
    if categories:
        categories_map = {k: v for k, v in MAGIC_ITEM_CATEGORIES.items() if k in categories}
        if not categories_map:
            raise RuntimeError("No valid magic item categories selected.")
    all_items: list[dict[str, str]] = []
    for item_type, url in categories_map.items():
        items = scrape_items_from_index(url, cache_dir, delay, force, limit, prefixes)
        for item in items:
            item["type"] = item_type
        all_items.extend(items)
        if not items:
            index_html = fetch_url(url, cache_dir, delay, force)
            table_items = parse_magic_table_items(index_html, item_type, prefixes)
            for item in table_items:
                item["type"] = item_type
            all_items.extend(table_items)

    existing = {}
    items_path = output_dir / "magic_items.json"
    if items_path.exists():
        try:
            existing = json.loads(items_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}

    combined = []
    combined.extend(existing.get("items", []))
    combined.extend(all_items)

    merged: dict[str, dict[str, str]] = {}
    for entry in combined:
        name = entry.get("name", "").strip()
        if not name:
            continue
        merged[name.lower()] = entry

    all_items = list(merged.values())

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "magic_items.json").write_text(
        json.dumps({"items": all_items}, indent=2),
        encoding="utf-8",
    )


def scrape_artifacts(
    cache_dir: Path,
    output_dir: Path,
    delay: float,
    force: bool,
    limit: int | None,
    categories: list[str] | None,
) -> None:
    categories_map = ARTIFACT_CATEGORIES
    if categories:
        categories_map = {k: v for k, v in ARTIFACT_CATEGORIES.items() if k in categories}
        if not categories_map:
            raise RuntimeError("No valid artifact categories selected.")
    artifacts: list[dict[str, str]] = []
    for url in categories_map.values():
        artifacts.extend(scrape_items_from_index(url, cache_dir, delay, force, limit, None))
    existing = {}
    artifacts_path = output_dir / "artifacts.json"
    if artifacts_path.exists():
        try:
            existing = json.loads(artifacts_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}

    combined = []
    combined.extend(existing.get("artifacts", []))
    combined.extend(artifacts)

    merged: dict[str, dict[str, str]] = {}
    for entry in combined:
        name = entry.get("name", "").strip()
        if not name:
            continue
        merged[name.lower()] = entry

    artifacts = list(merged.values())
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "artifacts.json").write_text(
        json.dumps({"artifacts": artifacts}, indent=2),
        encoding="utf-8",
    )


def scrape_equipment(cache_dir: Path, output_dir: Path, delay: float, force: bool) -> None:
    weapons_url = "https://www.d20pfsrd.com/equipment/weapons/"
    armor_url = "https://www.d20pfsrd.com/equipment/armor/"

    weapons = {
        "simple_melee": [],
        "simple_ranged": [],
        "simple_ammunition": [],
        "martial_melee": [],
        "martial_ranged": [],
        "martial_ammunition": [],
        "exotic_melee": [],
        "exotic_ranged": [],
        "exotic_ammunition": [],
    }

    weapons_html = fetch_url(weapons_url, cache_dir, delay, force)
    for table in re.findall(r"<table.*?</table>", weapons_html, flags=re.I | re.S):
        rows = parse_table_rows(table)
        if not rows:
            continue
        header_row = rows[0]
        header_text = [normalize_spaces(strip_tags(h)) for h in header_row]
        title = header_text[0] if header_text else ""
        category_key = WEAPON_CATEGORY_MAP.get(title)
        if not category_key:
            continue
        columns = [normalize_spaces(strip_tags(h)).lower() for h in header_text]
        for row in rows[1:]:
            if len(row) < len(columns):
                continue
            values = [normalize_spaces(strip_tags(cell)) for cell in row]
            name = values[0].replace("*", "").strip()
            if not name:
                continue
            entry = {
                "name": name,
                "cost": parse_number(values[1]) or 0,
                "damage_s": values[2],
                "damage_m": values[3],
                "critical": values[4],
                "range": parse_number(values[5]) or 0,
                "weight": parse_number(values[6]) or 0,
                "type": values[7],
                "special": parse_weapon_special(values[8]),
            }
            weapons[category_key].append(entry)

    armor = {"light": [], "medium": [], "heavy": [], "shields": []}
    armor_html = fetch_url(armor_url, cache_dir, delay, force)
    tables = re.findall(r"<table.*?</table>", armor_html, flags=re.I | re.S)
    for table in tables:
        if "Armor/Shield Bonus" not in table:
            continue
        rows = parse_table_rows(table)
        if not rows:
            continue
        current_section = None
        headers: list[str] = []
        expect_speed_subheader = False
        for row in rows:
            header_cells = [normalize_spaces(strip_tags(c)) for c in row if c]
            if not header_cells:
                continue
            if len(row) == 1:
                section_text = header_cells[0]
                if "Light" in section_text:
                    current_section = "light"
                elif "Medium" in section_text:
                    current_section = "medium"
                elif "Heavy" in section_text:
                    current_section = "heavy"
                elif "Shields" in section_text:
                    current_section = "shields"
                continue
            if "Armor/Shield Bonus" in header_cells:
                headers = [normalize_spaces(strip_tags(h)).lower() for h in row]
                if "speed" in headers:
                    expect_speed_subheader = True
                continue
            if expect_speed_subheader and ("30 ft." in header_cells or "20 ft." in header_cells):
                speed_index = headers.index("speed")
                headers.pop(speed_index)
                headers.insert(speed_index, "speed_30")
                headers.insert(speed_index + 1, "speed_20")
                expect_speed_subheader = False
                continue
            if not headers or not current_section:
                continue
            if len(row) < len(headers):
                continue
            values = [normalize_spaces(strip_tags(cell)) for cell in row]
            name = values[0].replace("*", "").strip()
            if not name:
                continue
            entry = {
                "name": name,
                "cost": parse_number(values[1]) or 0,
                "ac_bonus": parse_number(values[2]) or 0,
                "max_dex": parse_number(values[3]) or 0,
                "armor_check": parse_number(values[4]) or 0,
                "spell_failure": parse_percentage(values[5]) or 0,
                "speed_30": parse_number(values[6]) or 0,
                "speed_20": parse_number(values[7]) or 0,
                "weight": parse_number(values[8]) or 0,
            }
            armor[current_section].append(entry)

    existing_equipment = {}
    equipment_path = output_dir / "equipment.json"
    if equipment_path.exists():
        try:
            existing_equipment = json.loads(equipment_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_equipment = {}

    equipment = {
        "weapons": weapons or existing_equipment.get("weapons", {}),
        "armor": armor or existing_equipment.get("armor", {}),
        "adventuring_gear": existing_equipment.get("adventuring_gear", []),
        "potions": existing_equipment.get("potions", []),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "equipment.json").write_text(
        json.dumps(equipment, indent=2),
        encoding="utf-8",
    )


def scrape_classes(cache_dir: Path, output_dir: Path, delay: float, force: bool) -> None:
    classes_path = output_dir / "classes.json"
    existing = {}
    if classes_path.exists():
        existing = json.loads(classes_path.read_text(encoding="utf-8"))
    classes = existing.get("classes", [])
    if not classes:
        raise RuntimeError("classes.json missing or empty; cannot update class features.")

    for cls in classes:
        url = CLASS_URLS.get(cls.get("name", ""))
        if not url:
            continue
        html = fetch_url(url, cache_dir, delay, force)
        cls["features"] = parse_class_features(html)

    output_dir.mkdir(parents=True, exist_ok=True)
    classes_path.write_text(json.dumps({"classes": classes}, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape d20pfsrd PF1e content into JSON.")
    parser.add_argument("--spells", action="store_true", help="Scrape spells into data/srd/spells.json")
    parser.add_argument("--feats", action="store_true", help="Scrape feats into data/srd/feats.json")
    parser.add_argument("--classes", action="store_true", help="Update class features in data/srd/classes.json")
    parser.add_argument("--equipment", action="store_true", help="Scrape weapons/armor into data/srd/equipment.json")
    parser.add_argument("--magic-items", action="store_true", help="Scrape magic items into data/srd/magic_items.json")
    parser.add_argument("--artifacts", action="store_true", help="Scrape artifacts into data/srd/artifacts.json")
    parser.add_argument(
        "--pages",
        type=str,
        default=None,
        help="Comma-separated spell page keys (spells-a-d, spells-e-h, spells-i-l, spells-m-p, spells-q-t, spells-u-z).",
    )
    parser.add_argument(
        "--feat-pages",
        type=str,
        default=None,
        help="Comma-separated feat page keys (combat-feats, general-feats, item-creation-feats, metamagic-feats, teamwork-feats, critical-feats, performance-feats, racial-feats, skill-feats, style-feats).",
    )
    parser.add_argument(
        "--magic-item-types",
        type=str,
        default=None,
        help="Comma-separated magic item types (wondrous, weapons, armor, rings, rods, staves, wands, scrolls, potions).",
    )
    parser.add_argument(
        "--magic-item-prefixes",
        type=str,
        default=None,
        help="Comma-separated magic item prefixes (a-b, c-d, e-g, h-j, k-m, n-p, q-s, t-v, w-z).",
    )
    parser.add_argument(
        "--artifact-categories",
        type=str,
        default=None,
        help="Comma-separated artifact categories (minor-artifacts, major-artifacts).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of entries per category")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests (seconds)")
    parser.add_argument("--force", action="store_true", help="Ignore cache and refetch")
    parser.add_argument("--cache-dir", type=Path, default=Path("data/srd/_cache"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/srd"))
    args = parser.parse_args()

    if not (args.spells or args.feats or args.classes or args.equipment or args.magic_items or args.artifacts):
        parser.error("Select at least one scrape target.")

    pages = [p.strip() for p in args.pages.split(",")] if args.pages else None
    feat_pages = [p.strip() for p in args.feat_pages.split(",")] if args.feat_pages else None
    magic_types = [p.strip() for p in args.magic_item_types.split(",")] if args.magic_item_types else None
    magic_prefixes = [p.strip() for p in args.magic_item_prefixes.split(",")] if args.magic_item_prefixes else None
    artifact_categories = [p.strip() for p in args.artifact_categories.split(",")] if args.artifact_categories else None
    if args.spells:
        scrape_spells(args.cache_dir, args.output_dir, args.delay, args.force, args.limit, pages)
    if args.feats:
        scrape_feats(args.cache_dir, args.output_dir, args.delay, args.force, args.limit, feat_pages)
    if args.classes:
        scrape_classes(args.cache_dir, args.output_dir, args.delay, args.force)
    if args.equipment:
        scrape_equipment(args.cache_dir, args.output_dir, args.delay, args.force)
    if args.magic_items:
        scrape_magic_items(
            args.cache_dir,
            args.output_dir,
            args.delay,
            args.force,
            args.limit,
            magic_types,
            magic_prefixes,
        )
    if args.artifacts:
        scrape_artifacts(args.cache_dir, args.output_dir, args.delay, args.force, args.limit, artifact_categories)


if __name__ == "__main__":
    main()
