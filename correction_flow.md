# Rider Correction Flow

## User

The primary user is a motorcycle delivery rider in Kigali. The rider may use a low-end Android phone, may be offline for several hours, and may prefer a simple button workflow over typing long text. The dispatcher is the secondary user who reviews uncertain corrections.

## Correction Trigger

The rider reaches the area but discovers that the resolver pin is wrong, unclear, or too far from the customer. Instead of writing a paper report after the trip, the rider records a lightweight correction immediately.

## Input Modality

Primary modality: **three-button correction flow**.

1. **Pin too far**
2. **Wrong landmark**
3. **Cannot find customer**

Optional additions:

- 10-second voice note in Kinyarwanda, English, or French.
- One compressed photo if the phone supports it.
- Current GPS point captured automatically when available.

This is usable for semi-literate riders because the main action is button-based. Icons can be added later: distance icon, landmark icon, and help icon.

## Offline Workflow

When the rider is offline, the phone stores a small correction event locally:

```json
{
  "delivery_id": "D123",
  "landmark_id": "kimironko_market",
  "button": "pin_too_far",
  "gps_lat": -1.9369,
  "gps_lon": 30.1291,
  "timestamp": "2026-04-22T12:10:00",
  "voice_note_path": "optional",
  "photo_path": "optional"
}
```

The rider can continue working. No correction is lost because the event is queued until connectivity returns.

## Re-Sync

When internet returns, queued corrections sync to the backend. The backend groups corrections by:

- matched landmark;
- delivery zone;
- distance between rider GPS and current gazetteer pin;
- time window.

If a single rider reports an issue, the correction is marked low confidence. If two or more riders report similar corrections within 100 m, the correction is promoted for dispatcher review.

## Conflict Resolution

- **One correction:** store as weak evidence.
- **Two similar corrections within 100 m:** flag as likely gazetteer update.
- **Conflicting corrections:** send to dispatcher review.
- **Repeated unknown landmark descriptions:** create a candidate new landmark for the gazetteer.

The system does not automatically move important landmarks after one report.

## Data Volume Estimate

Assume one rider submits 40 corrections per month.

| Data item | Estimate |
|---|---:|
| Button event metadata | 1 KB each |
| 40 button events | 40 KB/month |
| Optional 10-second compressed voice note | 80 KB each |
| If 25% include voice notes | 10 x 80 KB = 800 KB/month |
| Optional compressed photo | 100 KB each |
| If 10% include photos | 4 x 100 KB = 400 KB/month |
| Estimated total | 1.2-1.5 MB/rider/month |

This is practical for low bandwidth because the default correction is only a button event plus coordinates. Voice and photo are optional.

## Why Cheaper Than Paper Bug Reports

Paper reports require the rider to remember the issue, return to a depot, write or explain the problem, and wait for someone to transcribe it. That creates delays, transcription errors, and staff time costs.

The digital correction flow is cheaper per correction because it is timestamped, geotagged, stored offline, synced automatically, and grouped with similar reports. A dispatcher reviews fewer, better-structured cases instead of reading many paper notes.

## Local Context Trade-Off

The workflow assumes riders are the ground truth but avoids trusting a single correction too much. This balances speed with safety: rider feedback improves the gazetteer, while conflict resolution prevents one mistaken report from corrupting the map.
