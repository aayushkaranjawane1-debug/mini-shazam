Put 5-10 short audio files here (wav/mp3/flac/ogg/m4a) to act as the
"known songs" database.

Naming: the file's base name (without extension) becomes the song's display
name in the app, so name them nicely, e.g.:

  library/
    daft_punk_one_more_time.mp3
    beethoven_fur_elise.wav
    queen_bohemian_rhapsody.mp3
    ...

After adding files, run (from the mini-shazam/ folder):

  python build_database.py

That fingerprints every file here and writes db.pkl. Then:

  streamlit run app.py

Delete this README.txt or leave it — build_database.py only reads audio files.
