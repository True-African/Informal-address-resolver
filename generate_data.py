"""Generate the exact local dataset shape requested in the T1.2 brief.

Files produced:
- data/descriptions.csv: 200 rows with {description_text, language_hint_optional}
- data/gazetteer.json: 50 landmarks with name, aliases, type, lat, lon, district
- data/gold.csv: 50 rows with {description_id, true_lat, true_lon}

Because descriptions.csv has no description_id column in the brief, IDs are
implicit: D001 is row 1, D002 is row 2, and so on.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from resolver import apply_offset


RANDOM_SEED = 42
DATA_DIR = Path(__file__).resolve().parent / "data"
GAZETTEER_PATH = DATA_DIR / "gazetteer.json"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
KIGALI_BBOX = (-2.08, 29.96, -1.84, 30.20)


LANDMARKS = [
    {"name": "RN3 Big Pharmacy", "aliases": ["big pharmacy", "pharmacy on rn3", "pharmacie rn3", "farumasi nini"], "type": "pharmacy", "lat": -1.957900, "lon": 30.112900, "district": "Gasabo"},
    {"name": "Kimironko Market", "aliases": ["kimironko", "isoko rya kimironko", "marche de kimironko", "kimironko market"], "type": "market", "lat": -1.936400, "lon": 30.130700, "district": "Gasabo"},
    {"name": "Nyabugogo Bus Park", "aliases": ["nyabugogo", "gare ya nyabugogo", "nyabugogo gare", "nyabugogo stop"], "type": "stop", "lat": -1.939900, "lon": 30.044600, "district": "Nyarugenge"},
    {"name": "Kacyiru Church", "aliases": ["eglise kacyiru", "itorero kacyiru", "kacyiru church"], "type": "church", "lat": -1.939900, "lon": 30.083700, "district": "Gasabo"},
    {"name": "Remera Taxi Park", "aliases": ["remera stop", "gare remera", "remera taxi", "gare ya remera"], "type": "stop", "lat": -1.954000, "lon": 30.108500, "district": "Gasabo"},
    {"name": "Remera Pharmacy", "aliases": ["pharmacie remera", "farumasi remera", "remera pharmacy"], "type": "pharmacy", "lat": -1.955300, "lon": 30.109800, "district": "Gasabo"},
    {"name": "Amahoro Stadium Stop", "aliases": ["amahoro stop", "gare amahoro", "amahoro stade", "gare ya amahoro"], "type": "stop", "lat": -1.955800, "lon": 30.113500, "district": "Gasabo"},
    {"name": "Kacyiru Market", "aliases": ["isoko rya kacyiru", "marche kacyiru", "kacyiru market"], "type": "market", "lat": -1.936700, "lon": 30.081300, "district": "Gasabo"},
    {"name": "Kigali Heights Pharmacy", "aliases": ["heights pharmacy", "pharmacie kigali heights", "farumasi ya heights"], "type": "pharmacy", "lat": -1.954700, "lon": 30.093900, "district": "Gasabo"},
    {"name": "Kigali Heights Stop", "aliases": ["heights stop", "gare kigali heights", "heights bus stop"], "type": "stop", "lat": -1.954900, "lon": 30.094500, "district": "Gasabo"},
    {"name": "Kimironko Church", "aliases": ["eglise kimironko", "itorero rya kimironko", "kimironko church"], "type": "church", "lat": -1.934800, "lon": 30.130000, "district": "Gasabo"},
    {"name": "Kimironko Pharmacy", "aliases": ["pharmacie kimironko", "farumasi kimironko", "kimironko pharmacy"], "type": "pharmacy", "lat": -1.937200, "lon": 30.129900, "district": "Gasabo"},
    {"name": "Kibagabaga Market", "aliases": ["isoko kibagabaga", "marche kibagabaga", "kibagabaga market"], "type": "market", "lat": -1.918900, "lon": 30.116000, "district": "Gasabo"},
    {"name": "Kibagabaga Church", "aliases": ["eglise kibagabaga", "itorero kibagabaga", "kibagabaga church"], "type": "church", "lat": -1.920200, "lon": 30.114800, "district": "Gasabo"},
    {"name": "Kibagabaga Pharmacy", "aliases": ["pharmacie kibagabaga", "farumasi kibagabaga", "kibagabaga pharmacy"], "type": "pharmacy", "lat": -1.919500, "lon": 30.117100, "district": "Gasabo"},
    {"name": "Gisozi Market", "aliases": ["isoko gisozi", "marche gisozi", "gisozi market"], "type": "market", "lat": -1.930800, "lon": 30.063000, "district": "Gasabo"},
    {"name": "Gisozi Church", "aliases": ["eglise gisozi", "itorero gisozi", "gisozi church"], "type": "church", "lat": -1.932000, "lon": 30.061800, "district": "Gasabo"},
    {"name": "Gisozi Stop", "aliases": ["gare gisozi", "gisozi bus stop", "gare ya gisozi"], "type": "stop", "lat": -1.931200, "lon": 30.059800, "district": "Gasabo"},
    {"name": "Kagugu Market", "aliases": ["isoko kagugu", "marche kagugu", "kagugu market"], "type": "market", "lat": -1.908600, "lon": 30.084400, "district": "Gasabo"},
    {"name": "Kagugu Pharmacy", "aliases": ["pharmacie kagugu", "farumasi kagugu", "kagugu pharmacy"], "type": "pharmacy", "lat": -1.907800, "lon": 30.085300, "district": "Gasabo"},
    {"name": "Kinyinya Church", "aliases": ["eglise kinyinya", "itorero kinyinya", "kinyinya church"], "type": "church", "lat": -1.906100, "lon": 30.104300, "district": "Gasabo"},
    {"name": "Kinyinya Stop", "aliases": ["gare kinyinya", "kinyinya bus stop", "gare ya kinyinya"], "type": "stop", "lat": -1.905500, "lon": 30.105600, "district": "Gasabo"},
    {"name": "Zindiro Market", "aliases": ["isoko zindiro", "marche zindiro", "zindiro market"], "type": "market", "lat": -1.921900, "lon": 30.156800, "district": "Gasabo"},
    {"name": "Zindiro Pharmacy", "aliases": ["pharmacie zindiro", "farumasi zindiro", "zindiro pharmacy"], "type": "pharmacy", "lat": -1.922800, "lon": 30.155900, "district": "Gasabo"},
    {"name": "Batsinda Stop", "aliases": ["gare batsinda", "batsinda bus stop", "gare ya batsinda"], "type": "stop", "lat": -1.893700, "lon": 30.083500, "district": "Gasabo"},
    {"name": "Kigali City Market", "aliases": ["city market", "marche de la ville", "isoko ryo mu mujyi"], "type": "market", "lat": -1.944700, "lon": 30.061700, "district": "Nyarugenge"},
    {"name": "UTC Pharmacy", "aliases": ["pharmacie utc", "farumasi utc", "utc pharmacy"], "type": "pharmacy", "lat": -1.948100, "lon": 30.062000, "district": "Nyarugenge"},
    {"name": "Sainte Famille Church", "aliases": ["eglise sainte famille", "sainte famille", "itorero sainte famille"], "type": "church", "lat": -1.943500, "lon": 30.061000, "district": "Nyarugenge"},
    {"name": "Nyamirambo Market", "aliases": ["isoko nyamirambo", "marche nyamirambo", "nyamirambo market"], "type": "market", "lat": -1.975200, "lon": 30.040800, "district": "Nyarugenge"},
    {"name": "Nyamirambo Stop", "aliases": ["gare nyamirambo", "nyamirambo bus stop", "gare ya nyamirambo"], "type": "stop", "lat": -1.976600, "lon": 30.043900, "district": "Nyarugenge"},
    {"name": "Nyamirambo Church", "aliases": ["eglise nyamirambo", "itorero nyamirambo", "nyamirambo church"], "type": "church", "lat": -1.977900, "lon": 30.044700, "district": "Nyarugenge"},
    {"name": "Biryogo Market", "aliases": ["isoko biryogo", "marche biryogo", "biryogo market"], "type": "market", "lat": -1.956200, "lon": 30.052200, "district": "Nyarugenge"},
    {"name": "Biryogo Pharmacy", "aliases": ["pharmacie biryogo", "farumasi biryogo", "biryogo pharmacy"], "type": "pharmacy", "lat": -1.955600, "lon": 30.052900, "district": "Nyarugenge"},
    {"name": "Kiyovu Church", "aliases": ["eglise kiyovu", "itorero kiyovu", "kiyovu church"], "type": "church", "lat": -1.956100, "lon": 30.067200, "district": "Nyarugenge"},
    {"name": "Kiyovu Market", "aliases": ["isoko kiyovu", "marche kiyovu", "kiyovu market"], "type": "market", "lat": -1.956000, "lon": 30.067400, "district": "Nyarugenge"},
    {"name": "Kimisagara Market", "aliases": ["isoko kimisagara", "marche kimisagara", "kimisagara market"], "type": "market", "lat": -1.971600, "lon": 30.055900, "district": "Nyarugenge"},
    {"name": "Kimisagara Stop", "aliases": ["gare kimisagara", "kimisagara bus stop", "gare ya kimisagara"], "type": "stop", "lat": -1.970900, "lon": 30.056700, "district": "Nyarugenge"},
    {"name": "Gitega Church", "aliases": ["eglise gitega", "itorero gitega", "gitega church"], "type": "church", "lat": -1.958900, "lon": 30.056900, "district": "Nyarugenge"},
    {"name": "Kicukiro Market", "aliases": ["isoko kicukiro", "marche kicukiro", "kicukiro market"], "type": "market", "lat": -1.994600, "lon": 30.105000, "district": "Kicukiro"},
    {"name": "Kicukiro Bus Park", "aliases": ["gare kicukiro", "kicukiro bus park", "gare ya kicukiro"], "type": "stop", "lat": -1.992900, "lon": 30.101500, "district": "Kicukiro"},
    {"name": "Kicukiro Pharmacy", "aliases": ["pharmacie kicukiro", "farumasi kicukiro", "kicukiro pharmacy"], "type": "pharmacy", "lat": -1.994100, "lon": 30.111200, "district": "Kicukiro"},
    {"name": "Kicukiro Church", "aliases": ["eglise kicukiro", "itorero kicukiro", "kicukiro church"], "type": "church", "lat": -1.993700, "lon": 30.108800, "district": "Kicukiro"},
    {"name": "Sonatubes Stop", "aliases": ["sonatubes", "gare sonatubes", "sonatubes bus stop"], "type": "stop", "lat": -1.970800, "lon": 30.104400, "district": "Kicukiro"},
    {"name": "Gatenga Market", "aliases": ["isoko gatenga", "marche gatenga", "gatenga market"], "type": "market", "lat": -1.999000, "lon": 30.091200, "district": "Kicukiro"},
    {"name": "Gatenga Church", "aliases": ["eglise gatenga", "itorero gatenga", "gatenga church"], "type": "church", "lat": -1.998200, "lon": 30.092100, "district": "Kicukiro"},
    {"name": "Gatenga Pharmacy", "aliases": ["pharmacie gatenga", "farumasi gatenga", "gatenga pharmacy"], "type": "pharmacy", "lat": -1.997800, "lon": 30.090400, "district": "Kicukiro"},
    {"name": "Nyarugunga Market", "aliases": ["isoko nyarugunga", "marche nyarugunga", "nyarugunga market"], "type": "market", "lat": -1.981600, "lon": 30.145100, "district": "Kicukiro"},
    {"name": "Nyarugunga Stop", "aliases": ["gare nyarugunga", "nyarugunga bus stop", "gare ya nyarugunga"], "type": "stop", "lat": -1.981000, "lon": 30.144200, "district": "Kicukiro"},
    {"name": "Kabeza Pharmacy", "aliases": ["pharmacie kabeza", "farumasi kabeza", "kabeza pharmacy"], "type": "pharmacy", "lat": -1.976500, "lon": 30.128300, "district": "Kicukiro"},
    {"name": "Kabeza Church", "aliases": ["eglise kabeza", "itorero kabeza", "kabeza church"], "type": "church", "lat": -1.975700, "lon": 30.127500, "district": "Kicukiro"},
]

MODIFIERS = [
    ("behind", "behind {alias}, red gate"),
    ("behind", "inyuma ya {alias}, gate itukura"),
    ("behind", "derriere {alias}, portail rouge"),
    ("near", "near {alias}"),
    ("near", "hafi ya {alias}"),
    ("near", "pres de {alias}"),
    ("opposite", "opposite {alias}"),
    ("opposite", "en face de {alias}"),
    ("above", "above {alias}"),
    ("above", "hejuru ya {alias}"),
]


def normalize_name(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def overpass_query() -> str:
    south, west, north, east = KIGALI_BBOX
    bbox = f"({south},{west},{north},{east})"
    return f"""
    [out:json][timeout:60];
    (
      node["amenity"="pharmacy"]["name"]{bbox};
      way["amenity"="pharmacy"]["name"]{bbox};
      relation["amenity"="pharmacy"]["name"]{bbox};
      node["amenity"="place_of_worship"]["name"]{bbox};
      way["amenity"="place_of_worship"]["name"]{bbox};
      relation["amenity"="place_of_worship"]["name"]{bbox};
      node["amenity"="marketplace"]["name"]{bbox};
      way["amenity"="marketplace"]["name"]{bbox};
      relation["amenity"="marketplace"]["name"]{bbox};
      node["highway"="bus_stop"]["name"]{bbox};
      node["public_transport"~"platform|station"]["name"]{bbox};
      way["public_transport"~"platform|station"]["name"]{bbox};
      relation["public_transport"~"platform|station"]["name"]{bbox};
    );
    out center tags;
    """


def fetch_overpass() -> dict[str, Any]:
    """Fetch Kigali landmarks from OpenStreetMap Overpass."""
    encoded = urllib.parse.urlencode({"data": overpass_query()}).encode("utf-8")
    request = urllib.request.Request(
        OVERPASS_URL,
        data=encoded,
        headers={"User-Agent": "AIMS-KTT-T1.2-Informal-Address-Resolver/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def osm_type(tags: dict[str, str]) -> str | None:
    if tags.get("amenity") == "pharmacy":
        return "pharmacy"
    if tags.get("amenity") == "marketplace":
        return "market"
    if tags.get("amenity") == "place_of_worship":
        return "church"
    if tags.get("highway") == "bus_stop" or tags.get("public_transport") in {"platform", "station"}:
        return "stop"
    return None


def element_lat_lon(element: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center")
    if center and "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None


def district_from_coords(lat: float, lon: float, tags: dict[str, str]) -> str:
    if tags.get("addr:district"):
        return tags["addr:district"]
    if lon < 30.075:
        return "Nyarugenge"
    if lon > 30.120:
        return "Kicukiro" if lat < -1.955 else "Gasabo"
    return "Kicukiro" if lat < -1.965 else "Gasabo"


def aliases_for(name: str, typ: str, tags: dict[str, str]) -> list[str]:
    aliases = {name}
    short = re.sub(r"\b(ltd|limited|plc|sarl|center|centre)\b", "", name, flags=re.I).strip()
    if short:
        aliases.add(short)
    if typ == "pharmacy":
        aliases.update({f"pharmacie {name}", f"farumasi {name}", f"{name} pharmacy"})
    elif typ == "church":
        aliases.update({f"eglise {name}", f"itorero {name}", f"{name} church"})
    elif typ == "market":
        aliases.update({f"marche {name}", f"isoko {name}", f"{name} market"})
    elif typ == "stop":
        aliases.update({f"gare {name}", f"gare ya {name}", f"{name} stop", f"{name} bus stop"})
    for key in ("name:fr", "name:rw", "alt_name", "old_name", "short_name"):
        if tags.get(key):
            aliases.add(tags[key])
    return sorted(alias for alias in aliases if alias)


def osm_elements_to_landmarks(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert OSM elements to challenge gazetteer rows."""
    by_name: dict[str, dict[str, Any]] = {}
    for element in raw.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")
        typ = osm_type(tags)
        lat_lon = element_lat_lon(element)
        if not name or not typ or not lat_lon:
            continue
        lat, lon = lat_lon
        key = f"{normalize_name(name)}::{typ}"
        by_name[key] = {
            "name": name,
            "aliases": aliases_for(name, typ, tags),
            "type": typ,
            "lat": round(lat, 7),
            "lon": round(lon, 7),
            "district": district_from_coords(lat, lon, tags),
        }
    return sorted(by_name.values(), key=lambda row: (row["type"], row["name"].lower()))


def similar_to_selected(item: dict[str, Any], selected: list[dict[str, Any]]) -> bool:
    item_tokens = set(normalize_name(item["name"]).split())
    for other in selected:
        other_tokens = set(normalize_name(other["name"]).split())
        if item_tokens and other_tokens:
            overlap = len(item_tokens & other_tokens) / max(1, min(len(item_tokens), len(other_tokens)))
            if overlap >= 0.8:
                return True
    return False


def select_landmarks(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select 50 balanced landmarks and keep the required demo anchors."""
    selected = [dict(item) for item in LANDMARKS[:3]]
    targets = {"pharmacy": 13, "church": 13, "stop": 12, "market": 12}
    for typ, limit in targets.items():
        current = sum(1 for item in selected if item["type"] == typ)
        for item in items:
            if current >= limit:
                break
            if item["type"] == typ and not similar_to_selected(item, selected):
                selected.append(item)
                current += 1
    for item in items:
        if len(selected) >= 50:
            break
        if not similar_to_selected(item, selected):
            selected.append(item)
    if len(selected) < 50:
        raise RuntimeError(f"Only found {len(selected)} landmarks; keep the fallback gazetteer.")
    return selected[:50]


def refresh_osm_gazetteer() -> bool:
    """Refresh data/gazetteer.json from OpenStreetMap."""
    started = time.time()
    try:
        raw = fetch_overpass()
        landmarks = select_landmarks(osm_elements_to_landmarks(raw))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"OpenStreetMap refresh skipped: {exc}")
        print("Continuing with existing data/gazetteer.json or the bundled fallback landmarks.")
        return False

    GAZETTEER_PATH.write_text(json.dumps(landmarks, indent=2), encoding="utf-8")
    print(f"Fetched {len(raw.get('elements', []))} OSM elements.")
    print(f"Wrote {GAZETTEER_PATH} with {len(landmarks)} landmarks in {time.time() - started:.1f}s.")
    return True


def maybe_typo(text: str, rng: random.Random) -> str:
    """Inject one small typo in a minority of descriptions."""
    if rng.random() > 0.18 or len(text) < 8:
        return text
    positions = [idx for idx, char in enumerate(text) if char.isalpha()]
    if not positions:
        return text
    pos = rng.choice(positions)
    return text[:pos] + text[pos + 1 :]


def language_hint(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ["inyuma", "hafi", "hejuru", "itukura"]):
        return "KIN"
    if any(word in lower for word in ["derriere", "pres", "face", "portail", "marche", "eglise", "pharmacie"]):
        return "FR"
    return "EN"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate challenge-shaped local data.")
    parser.add_argument("--refresh-osm", action="store_true", help="Refresh data/gazetteer.json from OpenStreetMap")
    args = parser.parse_args()

    rng = random.Random(RANDOM_SEED)
    DATA_DIR.mkdir(exist_ok=True)

    if args.refresh_osm:
        refresh_osm_gazetteer()

    # Prefer existing gazetteer; fallback keeps the repo runnable offline.
    landmarks = LANDMARKS
    if GAZETTEER_PATH.exists():
        landmarks = json.loads(GAZETTEER_PATH.read_text(encoding="utf-8"))
        print("Using data/gazetteer.json as the landmark source.")

    if len(landmarks) != 50:
        raise ValueError(f"Expected 50 landmarks, got {len(landmarks)}")

    GAZETTEER_PATH.write_text(json.dumps(landmarks, indent=2), encoding="utf-8")

    descriptions = []
    truth_by_id = {}
    for idx in range(200):
        landmark = rng.choice(landmarks)
        modifier, template = rng.choice(MODIFIERS)
        alias = rng.choice([landmark["name"], *landmark["aliases"]])
        text = template.format(alias=alias)
        if rng.random() < 0.22:
            text += " on RN3"
        if rng.random() < 0.14:
            text += " :)"
        text = maybe_typo(text, rng)

        description_id = f"D{idx + 1:03d}"
        descriptions.append(
            {
                "description_text": text,
                "language_hint_optional": language_hint(text),
            }
        )
        lat, lon = apply_offset(float(landmark["lat"]), float(landmark["lon"]), modifier)
        truth_by_id[description_id] = {"description_id": description_id, "true_lat": lat, "true_lon": lon}

    seeded_ids = [f"D{i:03d}" for i in range(1, 26)]
    held_out_ids = [f"D{i:03d}" for i in range(101, 126)]
    gold_rows = [truth_by_id[description_id] for description_id in [*seeded_ids, *held_out_ids]]

    with (DATA_DIR / "descriptions.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["description_text", "language_hint_optional"])
        writer.writeheader()
        writer.writerows(descriptions)

    with (DATA_DIR / "gold.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["description_id", "true_lat", "true_lon"])
        writer.writeheader()
        writer.writerows(gold_rows)

    print("Wrote exact challenge-shaped dataset:")
    print(f"- descriptions.csv: {len(descriptions)} rows x {{description_text, language_hint_optional}}")
    print("- gazetteer.json: 50 landmarks with name, aliases, type, lat, lon, district")
    print("- gold.csv: 50 rows with 25 seeded IDs and 25 held-out IDs")


if __name__ == "__main__":
    main()
