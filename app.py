"""Streamlit UI for Mini Shazam.

Run with:  streamlit run app.py
Needs db.pkl (from build_database.py) and the original files in library/.
"""

import os
import io
import glob
import numpy as np
import streamlit as st

import librosa
import librosa.display
import matplotlib.pyplot as plt

from fingerprint import compute_spectrogram, SAMPLE_RATE
from match import load_db, match_audio, MIN_MATCH_SCORE

DB_PATH = "db.pkl"
LIBRARY_DIR = "library"

st.set_page_config(page_title="Mini Shazam", layout="wide")
st.title("🔊 Mini Shazam")
st.caption("Upload or record a short clip and I'll try to name the song "
           "using constellation-map fingerprinting.")


@st.cache_resource
def get_db():
    if not os.path.exists(DB_PATH):
        return None
    return load_db(DB_PATH)


def find_library_file(name):
    """Given a song's display name, locate its file in library/."""
    for path in glob.glob(os.path.join(LIBRARY_DIR, name + ".*")):
        return path
    return None


def draw_spectrogram(spec, title):
    fig, ax = plt.subplots(figsize=(6, 3))
    img = librosa.display.specshow(spec, sr=SAMPLE_RATE, x_axis="time",
                                   y_axis="log", ax=ax)
    ax.set_title(title)
    fig.colorbar(img, ax=ax, format="%+2.0f dB")
    fig.tight_layout()
    return fig


db = get_db()
if db is None:
    st.error(
        "No fingerprint database found. Add songs to `library/`, run "
        "`python build_database.py`, then reload this page."
    )
    st.stop()

st.success(f"Database loaded: {len(db['songs'])} known songs.")

# --- Input ------------------------------------------------------------------
tab_upload, tab_record = st.tabs(["📁 Upload", "🎙️ Record"])
audio_bytes = None
with tab_upload:
    uploaded = st.file_uploader("Query clip (wav/mp3, 5–15s)",
                                type=["wav", "mp3"])
    if uploaded is not None:
        audio_bytes = uploaded.read()
with tab_record:
    if hasattr(st, "audio_input"):
        recorded = st.audio_input("Record a query")
        if recorded is not None:
            audio_bytes = recorded.read()
    else:
        st.info("Your Streamlit version has no mic recorder. "
                "Upgrade Streamlit, or use the Upload tab.")

if not audio_bytes:
    st.info("Upload or record a clip to identify it.")
    st.stop()

st.audio(audio_bytes)

try:
    y, sr = librosa.load(io.BytesIO(audio_bytes), sr=SAMPLE_RATE, mono=True)
except Exception as e:
    st.error(f"Could not read that audio: {e}")
    st.stop()

best, results = match_audio(y, sr, db)
query_spec = compute_spectrogram(y, sr)

if best is None:
    st.subheader("❓ No match found")
    st.write("No song aligned confidently enough "
             f"(need score ≥ {MIN_MATCH_SCORE}).")
    if results:
        top = results[0]
        st.caption(f"Closest was **{top[1]}** with only score {top[2]}.")
    st.pyplot(draw_spectrogram(query_spec, "Your query"))
    st.stop()

song_id, name, score, offset = best
# Rough confidence: top score relative to the runner-up (or itself if alone).
runner_up = results[1][2] if len(results) > 1 else 0
denom = score + runner_up if (score + runner_up) > 0 else 1
confidence = score / denom

st.subheader(f"✅ Match: **{name}**")
c1, c2 = st.columns(2)
c1.metric("Alignment score", score)
c2.metric("Confidence", f"{confidence * 100:.0f}%")

# Side-by-side spectrograms for the visual "look, it matches" moment.
col_q, col_m = st.columns(2)
with col_q:
    st.pyplot(draw_spectrogram(query_spec, "Your query"))
with col_m:
    match_path = find_library_file(name)
    if match_path:
        ym, _ = librosa.load(match_path, sr=SAMPLE_RATE, mono=True, duration=30.0)
        st.pyplot(draw_spectrogram(compute_spectrogram(ym, sr),
                                   f"Library: {name}"))
    else:
        st.warning(f"Could not find the original file for '{name}' in "
                   f"{LIBRARY_DIR}/ to display its spectrogram.")

with st.expander("All candidates"):
    for sid, nm, sc, off in results[:5]:
        st.write(f"- **{nm}** — score {sc}, offset {off}")
