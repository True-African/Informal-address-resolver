# T1.2 Informal Address Resolver

CPU-only resolver for informal delivery addresses in Kigali-style logistics settings.

The resolver converts mixed English, French, and Kinyarwanda address descriptions into coordinates using:

- OpenStreetMap-style landmark gazetteer data;
- fuzzy landmark matching;
- spatial direction rules such as `behind`, `inyuma ya`, `derriere`, `near`, and `opposite`;
- confidence scoring and an explainable rationale.

## Output Shape

```python
{
    "lat": float | None,
    "lon": float | None,
    "confidence": float,
    "matched_landmark": str | None,
    "rationale": str
}
```

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it using the command for your terminal:

```bash
# Windows Git Bash
source .venv/Scripts/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux, macOS, or Colab
source .venv/bin/activate
```

Install packages:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run the same commands through the environment Python:

```powershell
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Required Demo

```bash
python -c "from resolver import resolve; print(resolve('inyuma ya big pharmacy on RN3, red gate'))"
```

Example output:

```python
{
    "lat": -1.9584,
    "lon": 30.1129,
    "confidence": 1.0,
    "matched_landmark": "RN3 Big Pharmacy",
    "rationale": "Matched alias 'RN3 Big Pharmacy' for landmark 'RN3 Big Pharmacy' with score 100.0; modifier 'behind' from phrase 'inyuma' applied."
}
```

Exact coordinates may differ slightly depending on the gazetteer and offset calculation.

## Generate Data

The repository already includes generated sample data under `data/`.

To regenerate the challenge-shaped dataset:

```bash
python generate_data.py
```

This produces:

- `data/descriptions.csv`: 200 rows with `description_text, language_hint_optional`;
- `data/gazetteer.json`: 50 landmarks with `name, aliases, type, lat, lon, district`;
- `data/gold.csv`: 50 rows with `description_id, true_lat, true_lon`.

Because `descriptions.csv` has no `description_id` column, IDs are implicit: `D001` is row 1, `D002` is row 2, and so on.

Optional OpenStreetMap refresh:

```bash
python generate_data.py --refresh-osm
```

This only tries to rebuild `data/gazetteer.json` from OpenStreetMap/Overpass. The submitted resolver does not make network calls. If Overpass times out, the script continues with the existing local gazetteer or bundled fallback landmarks.

## Run Tests

```bash
python -m unittest discover -s tests
```

## Evaluation

```bash
python resolver.py --eval
```

The evaluation reports:

- mean haversine error in meters;
- percent of predictions within 100 m;
- percent of predictions within 300 m;
- five highest-error cases for analysis.

`eval.ipynb` is included as an optional notebook version of the same evaluation flow.

## Model / Checkpoint

N/A. This Tier 1 submission uses a CPU-only rule-based and fuzzy-matching resolver. No trained model or checkpoint is produced. The full algorithm is in `resolver.py`.

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

## Product and Business Adaptation

See `correction_flow.md` for the low-bandwidth rider correction workflow, including offline storage, sync behavior, conflict resolution, estimated data volume, and why the process is cheaper than paper bug reports.

## Known Limitations

- The resolver depends on the coverage and aliases in the gazetteer.
- Unknown landmarks are escalated instead of guessed.
- Directional offsets are approximate.
- Descriptions with multiple landmarks may choose the strongest fuzzy match.
- This is a Tier 1 baseline designed for clarity, speed, and live defense.

## Video

4-minute video URL: TODO paste unlisted YouTube/Vimeo/Drive link here.

## Process and Honor Code

See `process_log.md` and `SIGNED.md`.
