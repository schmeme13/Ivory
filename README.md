# Ivory

## Expressive rhythm interpretation

The default Expressive mode clusters different pitches struck within a bounded window (up to 90 ms), then favors sixteenth-note rhythms and fills tiny release gaps. Clustering happens across both staves; repeated attacks of the same pitch are kept separate. Simple favors eighth notes with a slightly wider chord window. Precise retains a thirty-second grid and distinct staggered attacks. These choices can simplify intentional ornaments; use Precise for those passages. Raw performance MIDI and detected-performance playback remain unchanged.

Leaving tempo blank refines the beat tracker's global tempo estimate against note attacks within a small neighborhood. A supplied tempo is honored. This is still constant-tempo quantization, not full rubato tracking. Accidental spelling is selected against the key signature without changing MIDI pitch; unexpected chromatic notes are not automatically deleted or moved into the key.

## Update 0.2: playback and notation repair

The result now has two separately labeled, locally synthesized audio previews: **Detected performance** uses raw model notes and pedal events; **Written score** uses exactly the pitches and durations exported to MusicXML. These are simple harmonic tones, not a sampled piano. The uploaded recording remains a separately labeled reference player. Starting one pauses the others.

Notation now groups notes by attack, uses a thirty-second grid, chooses clefs from each staff's range, estimates a staff boundary for high-register pieces, and spells accidentals consistently with the estimated key. A manual MIDI-note staff split is available. This is explicitly a readable reduction: note endings within chords are grouped and may be shortened to the next attack on that staff. It does not recover independent sustained voices or guarantee the original composer's notation. Pitch estimates are unchanged.

Completed jobs with `details.json` are restored on restart and the latest is loaded automatically. Playback files are `performance.wav` and `score.wav`; `score-events.json` records the written-score playback. Existing sample notation was backed up as `score-before-v02.musicxml` before regeneration. Version 0.1 details below describe the original baseline.

A local, research-based first iteration of audio-to-sheet-music transcription for solo piano.

## Start

Double-click **Start Ivory.cmd**, then use http://127.0.0.1:8765 in your browser. Keep the launcher window open while working. Closing it stops the service.

Choose a WAV, FLAC, MP3, or OGG recording (up to 2 minutes / 40 MB), set the meter, optionally enter a tempo, and click **Transcribe recording**. CPU processing can take several minutes, especially on the first run. Download MusicXML for editing in a notation program, MIDI for the actual detected performance, or JSON for note/pedal events. **Print / Save PDF** uses the browser print dialog after rendering the score.

If dependencies are missing, open PowerShell in this folder and run `powershell -ExecutionPolicy Bypass -File setup.ps1`. Python 3.12 is the tested interpreter. Installation downloads the authors' approximately 165 MB model. The score renderer is vendored locally; uploads do not leave your machine.

## What this iteration implements

- A FastAPI service and local web interface, with a single inference worker and job status polling.
- The authors' pretrained joint note/pedal CRNN: pitch, onset, offset, velocity, and sustain events. CPU or CUDA chosen automatically.
- Performance MIDI with sustain controller events; raw event JSON remains separate from estimated notation.
- Global tempo estimate from librosa beat tracking, editable tempo and meter, estimated key via music21.
- Sixteenth-note quantization; grouping simultaneous notes into chords; overlap allocation into voices; a middle-C staff split; barline ties and MusicXML engraving.
- Local sheet preview via OpenSheetMusicDisplay 1.9.2, print-to-PDF, input validation, and useful error states.

## Current limits

This is an integration baseline, not a newly trained model or a demonstrated accuracy improvement. Tempo is constant in the score, meter is supplied by the user (default 4/4), hand assignment is a pitch split, and rhythm quantization is heuristic. Pickups, rubato, swing, tuplets, sophisticated voice separation, note spelling, and crossed hands need review. In 6/8, BPM means quarter notes. Pedal events are exported in MIDI/JSON but not yet engraved; exact key releases under pedal are inherently uncertain. No calibrated confidence score or note editor is included yet. There is no authenticated public hosting or durable job history API. The server binds to loopback only. Jobs disappear from the API on restart, while their files remain under `data/jobs`; delete those folders when no longer needed.

## Research and provenance

- Kong et al., *High-resolution Piano Transcription with Pedals by Regressing Onset and Offset Times*: https://arxiv.org/abs/2010.01815 — basis for acoustic inference. Reported MAESTRO onset F1 is a benchmark metric, not finished-sheet accuracy.
- Authors' inference package: https://github.com/qiuqiangkong/piano_transcription_inference — `piano-transcription-inference==0.0.6`, MIT code. The training repository is archived; this adapter isolates the older implementation.
- Authors' checkpoint: https://zenodo.org/records/4034264 — downloader checks the published checksum and records provenance in `data/models/source.json`.
- Zeng et al., *End-to-End Real-World Polyphonic Piano Audio-to-Score Transcription with Hierarchical Decoding*: https://www.ijcai.org/proceedings/2024/862 — informs the separation of performance detection and score reconstruction. This project does not implement that paper's model.
- MAESTRO: https://magenta.tensorflow.org/datasets/maestro — candidate evaluation data, not bundled or used to train a new model here. Dataset licensing must be assessed before commercial training; do not assume an open-source code license covers data or weights.
- OpenSheetMusicDisplay: https://github.com/opensheetmusicdisplay/opensheetmusicdisplay — BSD-3-Clause renderer; license in `dist/vendor`.

## Development

Run `.venv/Scripts/python.exe -m pytest -q` from this directory. Tests exercise polyphony, barline ties, rejection of silent/invalid audio, and HTTP failures. These are correctness tests, not transcription-accuracy benchmarks.

Architecture: `ivory/transcription.py` handles acoustic inference; `ivory/notation.py` handles musical heuristics; `ivory/app.py` exposes the API; `dist/` is the web client. All model/download data lives under `data/`, excluded from Git. `requirements.txt` is the installation manifest; `requirements.lock.txt`, when present, records the verified environment.

The next milestone is a held-out audio/MIDI evaluation set covering different pianos, rooms, chord densities, and sustain usage. Measure note onset and offset F1, pedal event accuracy, notation corrections per minute, and latency independently. Then replace the global tempo/grid and staff split with beat-aware rhythm and voice models. Public service deployment will require a separate inference host, authentication, upload limits enforced before multipart parsing, retention controls, and durable job storage.
