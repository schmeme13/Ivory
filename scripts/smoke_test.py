"""Run real inference on a supplied short piano clip; no accuracy claim."""
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ivory.transcription import transcribe
from ivory.notation import make_score
from music21 import converter

source = Path(sys.argv[1])
output = Path(__file__).resolve().parents[1] / 'data/check/smoke'
output.mkdir(parents=True, exist_ok=True)
started = time.monotonic()
events = transcribe(source, output)
assert events['notes'], 'No notes detected in the smoke-test clip'
details = make_score(events, output)
score = converter.parse(output / 'score.musicxml')
assert len(score.parts) == 2
report = {'source': source.name, 'notes':len(events['notes']), 'pedals':len(events['pedals']), 'duration':events['duration'], 'elapsed_seconds':round(time.monotonic()-started,2), 'notation':details, 'accuracy_measured':False}
(output / 'report.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
