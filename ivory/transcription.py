"""Research-model adapter. Keep acoustic events separate from notation guesses."""
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
_model = None

def load_model():
    global _model
    if _model is None:
        checkpoint = ROOT / 'data/models/piano.pth'
        if not checkpoint.exists() or checkpoint.stat().st_size < 160_000_000:
            raise RuntimeError('The piano model is missing. Run setup.ps1 to download it.')
        import torch
        from piano_transcription_inference import PianoTranscription
        torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
        _model = PianoTranscription(checkpoint_path=str(checkpoint), device='cuda' if torch.cuda.is_available() else 'cpu')
    return _model

def transcribe(path: Path, output: Path):
    import soundfile as sf
    import librosa
    info = sf.info(path)
    if info.duration < 0.25 or info.duration > 120:
        raise ValueError('Choose a recording between 0.25 seconds and 2 minutes.')
    if info.channels > 2 or info.samplerate > 192000:
        raise ValueError('Use mono or stereo audio at 192 kHz or lower.')
    audio, sr = sf.read(path, dtype='float32', always_2d=True)
    audio = audio.mean(axis=1)
    if not np.isfinite(audio).all() or np.max(np.abs(audio)) < 1e-5:
        raise ValueError('The recording is silent or contains invalid samples.')
    audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
    result = load_model().transcribe(audio, None)
    notes = [dict(onset_time=float(n['onset_time']), offset_time=min(float(n['offset_time']), info.duration), midi_note=int(n['midi_note']), velocity=int(n['velocity'])) for n in result['est_note_events'] if 0 <= n['onset_time'] < info.duration and n['offset_time'] > n['onset_time']]
    pedals = [dict(onset_time=float(p['onset_time']), offset_time=min(float(p['offset_time']), info.duration)) for p in result['est_pedal_events'] if 0 <= p['onset_time'] < info.duration]
    from piano_transcription_inference.utilities import write_events_to_midi
    write_events_to_midi(0, notes, pedals, str(output / 'performance.mid'))
    bpm, beats = librosa.beat.beat_track(y=audio, sr=16000, units='time')
    return {'notes': notes, 'pedals': pedals, 'duration': info.duration, 'estimated_bpm': float(np.asarray(bpm).reshape(-1)[0]), 'beats': beats.tolist()}
