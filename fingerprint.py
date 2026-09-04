"""Audio fingerprinting, Shazam-style (simplified).

Pipeline:
  audio -> spectrogram -> local peaks ("constellation map")
        -> hash pairs of nearby peaks (f1, f2, dt) -> (hash, anchor_time)

All tunable knobs live at the top so you can make matching more/less forgiving
for a live demo. The defaults lean forgiving (works on short, noisy clips).
"""

import numpy as np
import librosa
from scipy.ndimage import maximum_filter

# --- Tunable parameters -----------------------------------------------------
SAMPLE_RATE = 22050        # everything runs at this rate
N_FFT = 2048               # STFT window size
HOP_LENGTH = 512           # STFT hop; time resolution = HOP_LENGTH / SR seconds

# Peak picking: a point is a peak if it's the local max in a neighborhood of
# this size (in spectrogram bins). Bigger -> fewer, stronger peaks.
PEAK_NEIGHBORHOOD_FREQ = 15
PEAK_NEIGHBORHOOD_TIME = 15
# Only keep peaks louder than (mean + this * std) of the dB spectrogram.
# Lower = more peaks = more forgiving (but noisier).
PEAK_MIN_AMP_STD = 0.5

# Pairing: an anchor peak is joined to peaks in a forward "target zone".
FAN_VALUE = 15             # how many following peaks to pair each anchor with
MIN_TIME_DELTA = 1         # min frames between anchor and target
MAX_TIME_DELTA = 100       # max frames between anchor and target


def compute_spectrogram(y, sr=SAMPLE_RATE):
    """Return a dB-scaled magnitude spectrogram (freq_bins x time_frames)."""
    stft = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP_LENGTH))
    return librosa.amplitude_to_db(stft, ref=np.max)


def find_peaks(spec):
    """Find local peaks in the spectrogram -> the constellation map.

    Returns a list of (freq_bin, time_frame) tuples, sorted by time.
    """
    # A bin is a local max if it equals the max within its neighborhood.
    footprint = np.ones((PEAK_NEIGHBORHOOD_FREQ, PEAK_NEIGHBORHOOD_TIME))
    local_max = maximum_filter(spec, footprint=footprint) == spec

    # Drop quiet peaks (background). Threshold relative to the spectrogram stats.
    threshold = spec.mean() + PEAK_MIN_AMP_STD * spec.std()
    detected = local_max & (spec > threshold)

    freqs, times = np.where(detected)
    peaks = list(zip(freqs.tolist(), times.tolist()))
    peaks.sort(key=lambda p: p[1])  # sort by time frame
    return peaks


def generate_hashes(peaks):
    """Turn a constellation map into fingerprint hashes.

    For each anchor peak, pair it with the next FAN_VALUE peaks that fall inside
    the time window. Each pair becomes a hash of (f1, f2, time_delta) plus the
    anchor's absolute time. Returns a list of (hash_int, anchor_time) tuples.
    """
    hashes = []
    n = len(peaks)
    for i in range(n):
        f1, t1 = peaks[i]
        for j in range(1, FAN_VALUE + 1):
            if i + j >= n:
                break
            f2, t2 = peaks[i + j]
            dt = t2 - t1
            if dt < MIN_TIME_DELTA or dt > MAX_TIME_DELTA:
                continue
            # Pack the three small integers into one hash. Each field is masked
            # so it stays inside its bit budget even if a value is large.
            h = ((f1 & 0x3FF) << 20) | ((f2 & 0x3FF) << 10) | (dt & 0x3FF)
            hashes.append((h, t1))
    return hashes


def fingerprint_audio(y, sr=SAMPLE_RATE):
    """Full pipeline: waveform -> (hashes, spectrogram, peaks)."""
    spec = compute_spectrogram(y, sr)
    peaks = find_peaks(spec)
    hashes = generate_hashes(peaks)
    return hashes, spec, peaks


def fingerprint_file(path, sr=SAMPLE_RATE, duration=None):
    """Load an audio file and fingerprint it. Returns (hashes, spec, peaks)."""
    y, sr = librosa.load(path, sr=sr, mono=True, duration=duration)
    return fingerprint_audio(y, sr)
