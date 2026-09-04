"""Fingerprint every file in library/ and save the lookup table to db.pkl.

Usage:
    python build_database.py

The database is a dict:
    {
      "hashes": { hash_int: [(song_id, anchor_time), ...], ... },
      "songs":  { song_id: "Display Name", ... },
    }
"""

import os
import glob
import pickle

from fingerprint import fingerprint_file

LIBRARY_DIR = "library"
DB_PATH = "db.pkl"
AUDIO_EXTS = ("*.wav", "*.mp3", "*.flac", "*.ogg", "*.m4a")


def collect_library_files():
    paths = []
    for ext in AUDIO_EXTS:
        paths.extend(glob.glob(os.path.join(LIBRARY_DIR, ext)))
    return sorted(paths)


def main():
    if not os.path.isdir(LIBRARY_DIR):
        raise SystemExit(
            f"'{LIBRARY_DIR}/' not found. Create it and add 5-10 audio files. "
            "See README.md."
        )

    files = collect_library_files()
    if not files:
        raise SystemExit(
            f"No audio files in '{LIBRARY_DIR}/'. Add some wav/mp3 songs first."
        )

    hash_table = {}   # hash_int -> list of (song_id, anchor_time)
    songs = {}        # song_id  -> display name

    for song_id, path in enumerate(files):
        name = os.path.splitext(os.path.basename(path))[0]
        songs[song_id] = name
        print(f"[{song_id}] fingerprinting {name} ...")
        hashes, _, peaks = fingerprint_file(path)
        for h, t in hashes:
            hash_table.setdefault(h, []).append((song_id, t))
        print(f"    {len(peaks)} peaks -> {len(hashes)} hashes")

    db = {"hashes": hash_table, "songs": songs}
    with open(DB_PATH, "wb") as f:
        pickle.dump(db, f)

    total = sum(len(v) for v in hash_table.values())
    print(f"\nSaved {DB_PATH}: {len(songs)} songs, "
          f"{len(hash_table)} unique hashes, {total} total entries.")


if __name__ == "__main__":
    main()
