# process_log.md

Candidate: Simeon  
Challenge: T1.2 Informal Address Resolver  
Date: 22 April 2026

## Timeline

Update this with the exact work you did during your 4-hour slot.

| Time | Work done |
|---|---|
| 00:00-00:30 | Read challenge brief, set repo structure, created README/LICENSE/SIGNED/process log |
| 00:30-01:30 | Built resolver baseline: normalization, fuzzy matching, modifier logic, confidence scoring |
| 01:30-02:30 | Added tests and evaluation metrics |
| 02:30-03:15 | Wrote correction_flow.md and README limitations |
| 03:15-03:45 | Recorded 4-minute video |
| 03:45-04:00 | Final tests, link checks, submission review |

## Declared LLM / Assistant Tools

| Tool | Purpose | What I changed myself |
|---|---|---|
| ChatGPT / Codex | Planning, repo scaffold, pseudocode review, documentation structure | TODO: Simeon should review, edit, test, and be ready to defend the final code and documents |
| OpenStreetMap / Overpass | Public landmark source for `data/gazetteer.json`, if network fetch is used | TODO: Simeon should verify the generated landmarks and explain that OSM is used only as data, not as a model |

## Three Sample Prompts I Used

1. "Help me interpret the T1.2 Informal Address Resolver requirements and produce a 4-hour execution plan."
2. "Scaffold the actual repo files for the submission, including resolver.py, tests, README, process_log.md, SIGNED.md, and correction_flow.md."
3. "Review my resolver design for fuzzy landmark matching, modifier detection, confidence scoring, and live-defense explainability."

## One Discarded Prompt

Discarded prompt: "Write the entire final submission for me without requiring me to understand it."

Reason: This would substitute my own work and make live defense dishonest. I used AI only for planning, scaffolding, and review support.

## Hardest Decision

TODO: Replace this paragraph with your own reflection.

The initial design decision was to use an OpenStreetMap gazetteer plus a simple interpretable fuzzy-matching baseline instead of a heavier ML model. This is defensible because the gazetteer is small, the task has strict CPU and latency constraints, and every step can be explained during live defense.
