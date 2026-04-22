"""Informal address resolver for AIMS KTT T1.2.

The resolver is intentionally small and explainable:
- normalize a noisy multilingual description;
- fuzzy-match a landmark from a local gazetteer;
- detect a spatial modifier;
- apply a simple coordinate offset;
- return confidence and rationale.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - fallback exists for bare Python environments.
    fuzz = None
    from difflib import SequenceMatcher

try:
    from geopy.distance import geodesic
except ImportError:  # pragma: no cover - fallback keeps the resolver runnable locally.
    geodesic = None


DATA_DIR = Path(__file__).resolve().parent / "data"
GAZETTEER_PATH = DATA_DIR / "gazetteer.json"
EARTH_RADIUS_M = 6_371_000


@dataclass(frozen=True)
class Landmark:
    name: str
    aliases: tuple[str, ...]
    type: str
    lat: float
    lon: float
    district: str


MODIFIER_PATTERNS: dict[str, tuple[str, ...]] = {
    "behind": ("behind", "at the back", "back of", "inyuma", "inyuma ya", "derriere", "arriere"),
    "near": ("near", "next to", "beside", "close to", "hafi", "hafi ya", "pres", "pres de", "a cote", "cote"),
    "opposite": ("opposite", "across", "facing", "en face", "imbere", "imbere ya"),
    "above": ("above", "uphill", "upper side", "hejuru", "hejuru ya"),
}

LANGUAGE_HINTS: dict[str, tuple[str, ...]] = {
    "EN": ("behind", "near", "opposite", "next to", "above", "gate", "market", "church", "stop"),
    "FR": ("derriere", "pres", "eglise", "marche", "pharmacie", "gare", "en face", "portail"),
    "KIN": ("inyuma", "hafi", "imbere", "hejuru", "isoko", "gare", "ku", "ya"),
}

GENERIC_TOKENS = {
    "a",
    "de",
    "du",
    "la",
    "le",
    "ya",
    "on",
    "the",
    "red",
    "gate",
    "portail",
    "itukura",
    "near",
    "hafi",
    "behind",
    "inyuma",
    "derriere",
    "opposite",
    "face",
    "en",
    "above",
    "hejuru",
    "pharmacy",
    "pharmacie",
    "farumasi",
    "market",
    "marche",
    "isoko",
    "church",
    "eglise",
    "itorero",
    "stop",
    "gare",
    "bus",
}


def normalize_text(text: str | None) -> str:
    """Lowercase, strip accents, remove punctuation/emoji, and collapse spaces."""
    if text is None:
        return ""
    # Stable matching starts with removing accents, emoji, and punctuation noise.
    lowered = str(text).lower()
    without_accents = "".join(
        ch for ch in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(ch)
    )
    asciiish = without_accents.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9]+", " ", asciiish)
    return re.sub(r"\s+", " ", cleaned).strip()


def detect_language_mix(text: str) -> list[str]:
    """Detect simple EN/FR/KIN keyword signals."""
    normalized = normalize_text(text)
    found = []
    for lang, hints in LANGUAGE_HINTS.items():
        if any(_contains_phrase(normalized, normalize_text(hint)) for hint in hints):
            found.append(lang)
    return found or ["unknown"]


def _contains_phrase(text: str, phrase: str) -> bool:
    if not phrase:
        return False
    return re.search(rf"(^|\s){re.escape(phrase)}($|\s)", text) is not None


def _score(a: str, b: str) -> float:
    """Return a 0-100 fuzzy score."""
    if not a or not b:
        return 0.0
    if fuzz is not None:
        return float(max(fuzz.partial_ratio(a, b), fuzz.token_set_ratio(a, b)))

    # Standard-library fallback for environments where rapidfuzz is not installed.
    full = SequenceMatcher(None, a, b).ratio() * 100
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    overlap = 0.0
    if a_tokens and b_tokens:
        overlap = 100 * len(a_tokens & b_tokens) / len(b_tokens)
    return max(full, overlap)


def _informative_tokens(text: str) -> set[str]:
    """Keep place-specific tokens and drop generic address words."""
    tokens = set(normalize_text(text).split())
    return {token for token in tokens if token not in GENERIC_TOKENS and not re.fullmatch(r"rn\d+", token)}


@lru_cache(maxsize=1)
def load_gazetteer() -> tuple[Landmark, ...]:
    """Load landmarks once; resolver calls stay fast after first load."""
    if not GAZETTEER_PATH.exists():
        raise FileNotFoundError(
            f"Gazetteer not found at {GAZETTEER_PATH}. Run `python generate_data.py` first."
        )
    raw = json.loads(GAZETTEER_PATH.read_text(encoding="utf-8"))
    landmarks = []
    for item in raw:
        landmarks.append(
            Landmark(
                name=item["name"],
                aliases=tuple(item.get("aliases", [])),
                type=item.get("type", "landmark"),
                lat=float(item["lat"]),
                lon=float(item["lon"]),
                district=item.get("district", "unknown"),
            )
        )
    return tuple(landmarks)


def match_landmark(text: str, gazetteer: tuple[Landmark, ...] | None = None) -> dict[str, Any]:
    """Return best landmark match, second score, and alias used."""
    normalized = normalize_text(text)
    gazetteer = gazetteer or load_gazetteer()
    candidates: list[dict[str, Any]] = []

    for landmark in gazetteer:
        aliases = (landmark.name, *landmark.aliases)
        for alias in aliases:
            normalized_alias = normalize_text(alias)
            score = _score(normalized, normalized_alias)
            informative_alias_tokens = _informative_tokens(normalized_alias)
            informative_overlap = len(_informative_tokens(normalized) & informative_alias_tokens)
            # Rank place-specific overlap above generic words like road, stop, or pharmacy.
            rank_score = score + min(12, 6 * informative_overlap)
            if not informative_overlap and informative_alias_tokens:
                rank_score -= 8
            if not informative_alias_tokens:
                rank_score -= 18
            candidates.append(
                {
                    "score": score,
                    "rank_score": rank_score,
                    "informative_overlap": informative_overlap,
                    "alias_token_count": len(normalized_alias.split()),
                    "landmark": landmark,
                    "alias": alias,
                    "normalized_alias": normalized_alias,
                }
            )

    # Prefer a specific multi-token alias when two aliases have the same score.
    candidates.sort(
        key=lambda item: (item["rank_score"], item["score"], item["informative_overlap"], item["alias_token_count"]),
        reverse=True,
    )
    best = candidates[0] if candidates else None
    second = None
    if best is not None:
        for candidate in candidates[1:]:
            if candidate["landmark"].name != best["landmark"].name:
                second = candidate
                break
    return {"best": best, "second": second}


def detect_modifier(text: str) -> dict[str, Any]:
    """Detect spatial relation and return a default of near."""
    normalized = normalize_text(text)
    for modifier, patterns in MODIFIER_PATTERNS.items():
        for pattern in patterns:
            if _contains_phrase(normalized, normalize_text(pattern)):
                return {"modifier": modifier, "matched_phrase": pattern, "found": True}
    return {"modifier": "near", "matched_phrase": "default", "found": False}


def apply_offset(lat: float, lon: float, modifier: str) -> tuple[float, float]:
    """Move a coordinate by a small deterministic offset."""
    distance_by_modifier = {
        "near": 20,
        "behind": 60,
        "opposite": 70,
        "above": 30,
    }
    bearing_by_modifier = {
        "near": 0,
        "behind": 180,
        "opposite": 90,
        "above": 0,
    }
    distance_m = distance_by_modifier.get(modifier, 20)
    bearing_deg = bearing_by_modifier.get(modifier, 0)
    return _destination_point(lat, lon, distance_m, bearing_deg)


def _destination_point(lat: float, lon: float, distance_m: float, bearing_deg: float) -> tuple[float, float]:
    """Use Geopy when installed; keep a math fallback for bare environments."""
    if geodesic is not None:
        point = geodesic(meters=distance_m).destination((lat, lon), bearing_deg)
        return round(point.latitude, 7), round(point.longitude, 7)

    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    bearing = math.radians(bearing_deg)
    angular_distance = distance_m / EARTH_RADIUS_M

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )
    return round(math.degrees(lat2), 7), round(math.degrees(lon2), 7)


def confidence_score(
    match_score: float,
    modifier_found: bool,
    language_signal: bool,
    ambiguity_gap: float,
) -> float:
    """Compute an interpretable confidence score in [0, 1]."""
    confidence = match_score / 100.0
    if modifier_found:
        confidence += 0.06
    if language_signal:
        confidence += 0.03
    if ambiguity_gap < 8:
        confidence -= 0.18
    elif ambiguity_gap < 15:
        confidence -= 0.08
    return max(0.0, min(1.0, round(confidence, 3)))


def _escalation_result(text: str, reason: str, languages: list[str] | None = None) -> dict[str, Any]:
    """Return a structured fallback instead of guessing blindly."""
    return {
        "lat": None,
        "lon": None,
        "confidence": 0.0,
        "matched_landmark": None,
        "rationale": reason,
        "modifier": None,
        "language_signals": languages or detect_language_mix(text),
        "escalation_required": True,
    }


def resolve(text: str) -> dict[str, Any]:
    """Resolve free text into lat/lon/confidence/matched_landmark/rationale."""
    normalized = normalize_text(text)
    if not normalized:
        return _escalation_result(str(text or ""), "Empty or non-text description; escalate to dispatcher.")

    languages = detect_language_mix(normalized)
    match = match_landmark(normalized)
    best = match["best"]
    second = match["second"]
    if best is None:
        return _escalation_result(text, "No gazetteer landmarks available.", languages)

    best_score = float(best["score"])
    second_score = float(second["score"]) if second else 0.0
    ambiguity_gap = best_score - second_score

    if best_score < 55:
        # Very weak matches are safer to escalate than to convert into a false pin.
        return _escalation_result(
            text,
            f"No confident landmark match. Best score was {best_score:.1f}; escalate to dispatcher.",
            languages,
        )

    modifier_info = detect_modifier(normalized)
    landmark: Landmark = best["landmark"]
    lat, lon = apply_offset(landmark.lat, landmark.lon, modifier_info["modifier"])
    confidence = confidence_score(
        match_score=best_score,
        modifier_found=bool(modifier_info["found"]),
        language_signal=languages != ["unknown"],
        ambiguity_gap=ambiguity_gap,
    )
    escalation_required = confidence < 0.62

    rationale = (
        f"Matched alias '{best['alias']}' for landmark '{landmark.name}' "
        f"with score {best_score:.1f}; modifier '{modifier_info['modifier']}' "
        f"from phrase '{modifier_info['matched_phrase']}' applied. "
        f"Second-best gap: {ambiguity_gap:.1f}."
    )
    if escalation_required:
        rationale += " Confidence is low enough to request dispatcher review."

    return {
        "lat": lat,
        "lon": lon,
        "confidence": confidence,
        "matched_landmark": landmark.name,
        "rationale": rationale,
        "modifier": modifier_info["modifier"],
        "language_signals": languages,
        "escalation_required": escalation_required,
    }


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two coordinates in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _load_descriptions() -> dict[str, str]:
    """Map implicit D001/D002 IDs to rows in descriptions.csv."""
    with (DATA_DIR / "descriptions.csv").open(encoding="utf-8") as f:
        return {f"D{idx:03d}": row["description_text"] for idx, row in enumerate(csv.DictReader(f), start=1)}


def evaluate_gold() -> dict[str, Any]:
    """Evaluate resolver output against gold.csv."""
    descriptions = _load_descriptions()
    with (DATA_DIR / "gold.csv").open(encoding="utf-8") as f:
        gold_rows = list(csv.DictReader(f))

    rows = []
    for gold in gold_rows:
        description_id = gold["description_id"]
        text = descriptions[description_id]
        pred = resolve(text)
        error_m = float("inf")
        if pred["lat"] is not None and pred["lon"] is not None:
            error_m = haversine_m(float(gold["true_lat"]), float(gold["true_lon"]), pred["lat"], pred["lon"])
        rows.append(
            {
                "description_id": description_id,
                "description_text": text,
                "matched_landmark": pred["matched_landmark"],
                "confidence": pred["confidence"],
                "error_m": error_m,
                "rationale": pred["rationale"],
            }
        )

    finite_errors = [row["error_m"] for row in rows if math.isfinite(row["error_m"])]
    return {
        "n": len(rows),
        "mean_haversine_error_m": sum(finite_errors) / len(finite_errors) if finite_errors else float("inf"),
        "within_100m": sum(1 for row in rows if row["error_m"] <= 100) / len(rows),
        "within_300m": sum(1 for row in rows if row["error_m"] <= 300) / len(rows),
        "worst_cases": sorted(rows, key=lambda row: row["error_m"], reverse=True)[:5],
    }


def print_evaluation() -> None:
    """Print the metrics expected in the challenge brief."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = evaluate_gold()
    print(f"Rows evaluated: {result['n']}")
    print(f"Mean haversine error: {result['mean_haversine_error_m']:.2f} m")
    print(f"Within 100 m: {result['within_100m']:.1%}")
    print(f"Within 300 m: {result['within_300m']:.1%}")
    print("\nFive highest-error cases:")
    for row in result["worst_cases"]:
        print(
            f"- {row['description_id']}: {row['error_m']:.1f} m | "
            f"{row['description_text']} -> {row['matched_landmark']} ({row['confidence']})"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resolve informal Kigali addresses.")
    parser.add_argument("--eval", action="store_true", help="Run gold.csv evaluation")
    parser.add_argument("--demo", action="store_true", help="Run the required demo input")
    parser.add_argument("text", nargs="*", help="Optional address text to resolve")
    args = parser.parse_args()

    if args.eval:
        print_evaluation()
    else:
        demo_text = " ".join(args.text) if args.text else "inyuma ya big pharmacy on RN3, red gate"
        print(resolve(demo_text))
