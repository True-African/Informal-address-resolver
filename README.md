# T1.2 Informal Address Resolver

CPU-only resolver for informal, multilingual delivery addresses in Kigali-style logistics settings.

The resolver takes a free-text address description and returns:

```python
{
    "lat": float | None,
    "lon": float | None,
    "confidence": float,
    "matched_landmark": str | None,
    "rationale": str
}
```

## Local Setup and Quick Run

Create a virtual environment:

```bash
python -m venv .venv
```

Install the required packages:

```bash
./.venv/Scripts/python.exe -m pip install --upgrade pip
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Run the required demo:

```bash
./.venv/Scripts/python.exe -c "from resolver import resolve; print(resolve('inyuma ya big pharmacy on RN3, red gate'))"
```

These commands use Git Bash on Windows. In PowerShell, use `& .\.venv\Scripts\python.exe` instead of `./.venv/Scripts/python.exe`.

The demo should work on a free Colab CPU. The repository includes generated sample data under `data/`. To regenerate it:

```bash
./.venv/Scripts/python.exe generate_data.py
```

Optional: to try rebuilding the gazetteer from live OpenStreetMap data first:

```bash
./.venv/Scripts/python.exe generate_data.py --refresh-osm
```

This uses OpenStreetMap/Overpass only to create the local `data/gazetteer.json`. The submitted resolver itself does not make network calls. If Overpass is slow or returns a gateway timeout, the script continues with the existing local gazetteer or the bundled fallback landmarks. For grading, `./.venv/Scripts/python.exe generate_data.py` is sufficient and works offline.

The generated files follow the challenge schema:

- `descriptions.csv`: 200 rows with only `description_text, language_hint_optional`.
- `gazetteer.json`: 50 landmarks with `name, aliases, type, lat, lon, district`.
- `gold.csv`: 50 rows with `description_id, true_lat, true_lon`.

Because the brief does not include `description_id` in `descriptions.csv`, IDs are implicit: `D001` is row 1, `D002` is row 2, and so on.

## What This Project Does

This submission resolves informal addresses such as:

- `inyuma ya big pharmacy on RN3, red gate`
- `derriere marche de kimironko, portail rouge`
- `hafi ya gare ya nyabugogo`

It uses a small deterministic pipeline:

1. Normalize noisy text.
2. Detect language clues from English, French, and Kinyarwanda keywords.
3. Fuzzy-match landmark names and aliases from `data/gazetteer.json`, which can be generated from OpenStreetMap.
4. Detect spatial modifiers such as `behind`, `inyuma ya`, `derriere`, `near`, and `opposite`.
5. Apply a small coordinate offset with Geopy when available, with a math fallback.
6. Return confidence and a rationale.

## Model / Checkpoint

N/A. This Tier 1 submission uses OpenStreetMap-derived gazetteer data plus a CPU-only rule-based and fuzzy-matching resolver. No trained model or checkpoint is produced. The algorithm is fully contained in `resolver.py` and can be run from the commands above.

## Repository Structure

```text
.
|-- README.md
|-- LICENSE
|-- requirements.txt
|-- resolver.py
|-- generate_data.py
|-- eval.ipynb
|-- correction_flow.md
|-- process_log.md
|-- SIGNED.md
|-- data/
|   |-- descriptions.csv
|   |-- gazetteer.json
|   `-- gold.csv
`-- tests/
    `-- test_resolver.py
```

## Run Tests

```bash
./.venv/Scripts/python.exe -m unittest discover -s tests
```

## Evaluation

```bash
./.venv/Scripts/python.exe resolver.py --eval
```

The evaluation reports:

- mean haversine error in meters;
- percent of predictions within 100 m;
- percent of predictions within 300 m;
- five highest-error cases for analysis.

You can also open `eval.ipynb` to inspect the same evaluation flow.

## Required Demo Command

```bash
./.venv/Scripts/python.exe -c "from resolver import resolve; print(resolve('inyuma ya big pharmacy on RN3, red gate'))"
```

Example output shape:

```python
{
    "lat": -1.9585,
    "lon": 30.1234,
    "confidence": 0.93,
    "matched_landmark": "RN3 Big Pharmacy",
    "rationale": "Matched alias 'big pharmacy' with score 100.0; modifier 'behind' applied."
}
```

Exact coordinates may differ depending on the gazetteer and modifier offset.

## Product and Business Adaptation

See `correction_flow.md` for the low-bandwidth rider correction workflow, including offline storage, sync behavior, conflict resolution, estimated data volume, and why the process is cheaper than paper bug reports.

## Known Limitations

- The resolver is only as good as the gazetteer aliases.
- Missing or unknown landmarks are escalated rather than guessed.
- Directional offsets are approximate and intentionally simple.
- Mixed descriptions with multiple landmarks may choose the strongest fuzzy match.
- This is a Tier 1 baseline, designed for clarity and live defense rather than maximum geographic accuracy.

## Video

4-minute video URL: TODO paste unlisted YouTube/Vimeo/Drive link here.

## Process and Honor Code

See `process_log.md` and `SIGNED.md`.
