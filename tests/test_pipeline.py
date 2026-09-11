import io
import time
import numpy as np
import pytest
from music21 import converter
from fastapi.testclient import TestClient
from ivory.app import app
from ivory.notation import make_score
from ivory.transcription import transcribe

def test_polyphony_and_barline_ties(tmp_path):
    events = {'estimated_bpm':120, 'notes':[
        {'midi_note':60,'onset_time':0,'offset_time':1},
        {'midi_note':64,'onset_time':0,'offset_time':1},
        {'midi_note':67,'onset_time':0.5,'offset_time':1.5},
        {'midi_note':48,'onset_time':0,'offset_time':3}]}
    details = make_score(events,tmp_path)
    score = converter.parse(tmp_path/'score.musicxml')
    assert len(score.parts) == 2
    assert {p.midi for p in score.flatten().pitches} == {48,60,64,67}
    assert any(n.tie is not None for n in score.parts[1].recurse().notes)
    assert details['meter'] == '4/4'
    assert events['notes'][2]['onset_time'] == 0.5

def test_invalid_and_silent_audio(tmp_path):
    import soundfile as sf
    source = tmp_path/'silent.wav'
    sf.write(source, np.zeros(16000), 16000)
    with pytest.raises(ValueError,match='silent'):
        transcribe(source,tmp_path)
    source.write_bytes(b'not audio')
    with pytest.raises(Exception):
        transcribe(source,tmp_path)

def test_api_validation_and_missing_job():
    client = TestClient(app)
    assert client.get('/').status_code == 200
    assert client.get('/api/jobs/missing').status_code == 404
    assert client.post('/api/jobs',files={'file':('empty.wav',b'')}).status_code == 400
    assert client.post('/api/jobs',files={'file':('x.wav',b'123')},data={'signature':'9/9'}).status_code == 422
    assert client.get('/api/jobs/missing/files/input.audio').status_code == 404
    assert client.post('/api/jobs', headers={'Origin':'https://example.com'}, files={'file':('x.wav',b'123')}).status_code == 403

def test_static_assets_exist():
    from html.parser import HTMLParser
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / 'dist'
    class Assets(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for name, value in attrs:
                if name in ('src','href') and value.startswith('/') and value != '/':
                    assert (root / value.lstrip('/')).is_file(), value
    Assets().feed((root/'index.html').read_text(encoding='utf-8'))

def test_invalid_audio_job_reports_failure():
    client = TestClient(app)
    response = client.post('/api/jobs',files={'file':('broken.wav',b'not an audio file')})
    assert response.status_code == 202
    job_id = response.json()['id']
    for _ in range(100):
        job = client.get('/api/jobs/'+job_id).json()
        if job['status'] == 'error': break
        time.sleep(.05)
    assert job['status'] == 'error'
    assert client.get(f'/api/jobs/{job_id}/files/score.musicxml').status_code == 409
