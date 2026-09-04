"""Match a query clip against db.pkl using time-offset histograms.

The idea: if a query really is a snippet of song X, then many of its matching
hashes will line up at the SAME relative time offset (query_anchor vs
db_anchor). We histogram those offsets per song; the tallest single bin is the
score. A real match produces one sharp spike; noise produces a flat spread.
"""

import pickle
from collections import defaultdict

from fingerprint import fingerprint_audio, fingerprint_file

# Minimum aligned-hash count to call something a match. Tuned to be forgiving
# for a live demo but high enough to reject random noise.
MIN_MATCH_SCORE = 5


def load_db(db_path="db.pkl"):
    with open(db_path, "rb") as f:
        return pickle.load(f)


def match_hashes(query_hashes, db):
    """Score every song against the query's hashes.

    Returns a sorted list of (song_id, name, score, best_offset), best first.
    """
    hash_table = db["hashes"]
    songs = db["songs"]

    # offset_counts[song_id][offset] = how many hashes align at that offset
    offset_counts = defaultdict(lambda: defaultdict(int))
    for h, q_time in query_hashes:
        if h not in hash_table:
            continue
        for song_id, db_time in hash_table[h]:
            offset = db_time - q_time
            offset_counts[song_id][offset] += 1

    results = []
    for song_id, offsets in offset_counts.items():
        best_offset, score = max(offsets.items(), key=lambda kv: kv[1])
        results.append((song_id, songs[song_id], score, best_offset))

    results.sort(key=lambda r: r[2], reverse=True)
    return results


def match_audio(y, sr, db):
    """Fingerprint a waveform and match it. Returns (best_or_None, all_results)."""
    query_hashes, _, _ = fingerprint_audio(y, sr)
    results = match_hashes(query_hashes, db)
    if not results:
        return None, results

    best = results[0]
    # Confidence heuristic: how dominant is the top song vs the runner-up.
    if best[2] < MIN_MATCH_SCORE:
        return None, results
    return best, results


def match_file(path, db, duration=None):
    """Convenience wrapper for matching a file on disk."""
    query_hashes, _, _ = fingerprint_file(path, duration=duration)
    results = match_hashes(query_hashes, db)
    if not results or results[0][2] < MIN_MATCH_SCORE:
        return None, results
    return results[0], results


if __name__ == "__main__":
    # Quick CLI: python match.py <query.wav>
    import sys
    if len(sys.argv) < 2:
        raise SystemExit("usage: python match.py <query_audio_file>")
    db = load_db()
    best, results = match_file(sys.argv[1], db)
    print("Top candidates (song, score, offset):")
    for song_id, name, score, offset in results[:5]:
        print(f"  {name:30s} score={score:4d} offset={offset}")
    if best is None:
        print("\n=> no match found")
    else:
        print(f"\n=> best match: {best[1]} (score {best[2]})")
