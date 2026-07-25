#!/usr/bin/env python3
"""
audio_analysis.py — Offline audio feature extraction for per-frame uniforms.

Analyzes a narration WAV with librosa, produces per-frame arrays of:
  - volume envelope
  - onset/beat strength
  - spectral centroid
  - RMS energy

These are baked into a lookup texture or uniform array, passed to the GLSL
shader as `u_audioVolume`, `u_audioBeat`, `u_audioSpectral` per frame.

Usage:
    python audio_analysis.py narration_full.wav --fps 24 --output audio_features.npy
    python audio_analysis.py narration_full.wav --fps 24 --output audio_features.json
"""
import argparse, json, sys
from pathlib import Path

import numpy as np


def analyze(audio_path: Path, fps: int = 24, smooth: float = 0.5, normalize_loudness: bool = True) -> dict:
    """Extract per-frame audio features from a WAV file.
    
    If normalize_loudness is True, applies EBU R128 loudness normalization
    (-23 LUFS) before analysis so u_audioVolume behaves consistently across
    different TTS voices and takes without re-tuning shader response curves.
    """
    try:
        import librosa
    except ImportError:
        raise RuntimeError("librosa required: pip install librosa")

    print(f"Analyzing: {audio_path}")

    # Load raw audio
    y, sr = librosa.load(str(audio_path), sr=None, mono=True)

    # Loudness normalization (EBU R128) for consistent volume envelope
    if normalize_loudness:
        try:
            import pyloudnorm as pyln
            meter = pyln.Meter(sr)
            loudness = meter.integrated_loudness(y)
            y = pyln.normalize.loudness(y, loudness, -23.0)
            print(f"  Loudness normalized: {loudness:.1f} LUFS → -23 LUFS")
        except ImportError:
            # Fallback: simple RMS normalization
            rms = np.sqrt(np.mean(y**2))
            if rms > 0:
                y = y * (0.1 / rms)
            print(f"  RMS normalized (pyloudnorm not available)")

    dur = len(y) / sr
    n_frames = max(2, round(dur * fps))

    print(f"  Duration: {dur:.1f}s, Sample rate: {sr}Hz, Frames: {n_frames}")

    # Per-frame timestamps
    times = np.linspace(0, dur, n_frames)

    # RMS energy envelope
    hop = max(1, len(y) // n_frames)
    rms = librosa.feature.rms(y=y, frame_length=hop * 4, hop_length=hop)[0]
    rms = np.interp(np.linspace(0, len(rms), n_frames), np.arange(len(rms)), rms)
    rms = rms / (rms.max() + 1e-8)  # normalize

    # Onset strength (beat likelihood)
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    onset = np.interp(np.linspace(0, len(onset), n_frames), np.arange(len(onset)), onset)
    onset = onset / (onset.max() + 1e-8)

    # Spectral centroid (brightness)
    cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop)[0]
    cent = np.interp(np.linspace(0, len(cent), n_frames), np.arange(len(cent)), cent)
    cent = (cent - cent.min()) / (cent.max() - cent.min() + 1e-8)

    # Apply smoothing
    if smooth > 0:
        from scipy.ndimage import gaussian_filter1d
        rms = gaussian_filter1d(rms, sigma=smooth * fps / 10)
        onset = gaussian_filter1d(onset, sigma=smooth * fps / 20)
        cent = gaussian_filter1d(cent, sigma=smooth * fps / 10)

    return {
        "fps": fps,
        "duration": dur,
        "n_frames": n_frames,
        "volume": rms.tolist(),
        "onset": onset.tolist(),
        "centroid": cent.tolist(),
        "beat": (onset > onset.mean() * 2.0).astype(float).tolist(),  # thresholded beat
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=str, help="Path to WAV file")
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--output", type=str, default="audio_features.json")
    parser.add_argument("--smooth", type=float, default=0.5)
    args = parser.parse_args()

    features = analyze(Path(args.audio), args.fps, args.smooth)

    out = Path(args.output)
    if out.suffix == ".npy":
        np.save(str(out), features)
    else:
        out.write_text(json.dumps(features, indent=2))
    print(f"Saved: {out}  ({features['n_frames']} frames)")
    print(f"  volume:  min={min(features['volume']):.3f} max={max(features['volume']):.3f}")
    print(f"  onset:   min={min(features['onset']):.3f} max={max(features['onset']):.3f}")
    print(f"  beats:   {sum(features['beat'])} detected")


if __name__ == "__main__":
    main()
