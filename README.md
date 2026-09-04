# Mini Shazam

A simplified, offline reimplementation of Shazam-style audio fingerprinting.
It builds a **constellation map** of spectrogram peaks, hashes pairs of peaks,
and identifies a short query clip by finding the song whose hashes line up at a
consistent time offset.

## Files

| File                | Purpose                                                       |
|---------------------|---------------------------------------------------------------|
| `fingerprint.py`    | Spectrogram → peaks → hashes. Tunable knobs at the top.       |
| `build_database.py` | Fingerprints everything in `library/` → `db.pkl`.             |
| `match.py`          | Fingerprints a query and finds the best-aligned song.         |
| `app.py`            | Streamlit demo UI with side-by-side spectrograms.             |
| `library/`          | Your "known songs" (5–10 short audio files).                  |

## Setup

```bash
pip install -r requirements.txt
```

## 1. Add songs

Drop 5–10 short audio files into `library/` (see `library/README.txt`). The
file's base name becomes the song's display name.

## 2. Build the database (run once per library change)

```bash
python build_database.py
```

This fingerprints every file and writes `db.pkl`.

## 3. Run the app

```bash
streamlit run app.py
```

Upload or record a 5–15s clip (a noisy phone recording of a library song is the
fun demo). The app shows the predicted song, a confidence score, and the query
spectrogram next to the matched song's spectrogram.

You can also match from the command line:

```bash
python match.py path/to/query.wav
```

## How it works (read this aloud during the demo)

> A song's spectrogram is a picture of which frequencies are loud over time. We
> pick out only the **peaks** — the brightest points — which gives a sparse
> "constellation" of dots that survives noise and compression far better than
> the full audio. We then take pairs of nearby peaks and turn each pair into a
> compact **hash** from the two frequencies and the time gap between them, tagged
> with when the anchor peak occurred. Every song in the library contributes its
> hashes to one big lookup table. To identify a clip, we fingerprint it the same
> way, look up each hash, and ask: for each candidate song, do the matches line
> up at a **consistent time offset**? A true match produces a sharp spike in the
> offset histogram — lots of hashes agreeing on the same alignment — while noise
> just scatters. The height of that spike is our confidence.

## Tuning for a forgiving live demo

All knobs live at the top of `fingerprint.py`:

- Lower `PEAK_MIN_AMP_STD` → more peaks → more forgiving of noisy clips.
- Raise `FAN_VALUE` → more hash pairs → more robust but larger `db.pkl`.
- `MIN_MATCH_SCORE` in `match.py` sets how confident a match must be before the
  app calls it (otherwise it honestly says **"no match found"** rather than
  guessing).

Everything runs offline once `library/` and `db.pkl` are set up — no API calls.
