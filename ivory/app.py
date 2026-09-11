from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from uuid import uuid4
import json
import logging
import shutil

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from .transcription import transcribe
from .notation import make_score
from .workshop import EditDocument, read_document, save_document

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/jobs'
DATA.mkdir(parents=True, exist_ok=True)
app = FastAPI(title='Ivory', version='0.2.0')
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])

@app.middleware('http')
async def local_requests(request, call_next):
    origin = request.headers.get('origin')
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and origin and origin not in ('http://127.0.0.1:8765', 'http://localhost:8765'):
        return JSONResponse({'detail': 'Open Ivory from its local address.'}, status_code=403)
    return await call_next(request)

pool = ThreadPoolExecutor(max_workers=1)
jobs = {}
lock = Lock()

class ScoreOptions(BaseModel):
    bpm: float | None = Field(default=None, ge=20, le=300)
    meter: Literal['4/4', '3/4', '2/4', '6/8'] = '4/4'
    split: int | None = Field(default=None, ge=21, le=108)
    feel: Literal['expressive', 'simple', 'precise'] = 'expressive'

def get_job(job_id):
    with lock:
        if job_id not in jobs:
            raise HTTPException(404, 'Recording not found. Jobs are available until the app restarts.')
        return dict(jobs[job_id])

def update(job_id, **values):
    with lock:
        jobs[job_id].update(values)

def process(job_id, options):
    folder = DATA / job_id
    try:
        update(job_id, status='transcribing', message='Listening for notes and pedal. This can take several minutes on CPU.')
        events = transcribe(folder / 'input.audio', folder)
        (folder / 'events.json').write_text(json.dumps(events, indent=2))
        if not events['notes']:
            raise ValueError('No piano notes were detected. Try a clearer solo-piano recording.')
        update(job_id, status='engraving', message='Preparing the score…')
        details = make_score(events, folder, options.bpm, options.meter, options.split, options.feel)
        update(job_id, status='done', message='Your first-pass score is ready.', details=details, note_count=len(events['notes']), pedal_count=len(events['pedals']), duration=events['duration'])
    except Exception as exc:
        logging.exception('Transcription failed')
        update(job_id, status='error', message=str(exc) if isinstance(exc, (ValueError, RuntimeError)) else 'Processing failed. See the local server log for details.')

@app.get('/api/health')
def health():
    model = ROOT / 'data/models/piano.pth'
    return {'model_ready': model.exists() and model.stat().st_size >= 160_000_000, 'version': '0.2.0'}

@app.get('/api/latest')
def latest():
    completed = [j for j in jobs.values() if j['status'] == 'done']
    return completed[-1] if completed else None

@app.post('/api/jobs', status_code=202)
async def upload(file: UploadFile = File(...), bpm: float | None = Form(None), signature: str = Form('4/4'), split: int | None = Form(None), feel: str = Form('expressive')):
    try:
        options = ScoreOptions(bpm=bpm, meter=signature, split=split, feel=feel)
    except ValueError:
        raise HTTPException(422, 'Use tempo 20–300 and a supported meter.')
    with lock:
        if any(j['status'] in ('uploading', 'queued', 'transcribing', 'engraving') for j in jobs.values()):
            raise HTTPException(409, 'A recording is already processing. Please wait for it to finish.')
        job_id = uuid4().hex
        jobs[job_id] = {'id': job_id, 'status': 'uploading', 'message': 'Receiving audio…'}
    folder = DATA / job_id
    folder.mkdir()
    try:
        size = 0
        with (folder / 'input.audio').open('wb') as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 40 * 1024 * 1024:
                    raise HTTPException(413, 'Maximum file size is 40 MB.')
                target.write(chunk)
        if not size:
            raise HTTPException(400, 'The file is empty.')
    except Exception:
        update(job_id, status='error', message='Upload failed.')
        shutil.rmtree(folder)
        raise
    finally:
        await file.close()
    update(job_id, status='queued', message='Waiting to transcribe…')
    pool.submit(process, job_id, options)
    return get_job(job_id)

@app.get('/api/jobs/{job_id}')
def status(job_id: str):
    return get_job(job_id)

@app.post('/api/jobs/{job_id}/score')
def rescore(job_id: str, options: ScoreOptions):
    if get_job(job_id)['status'] != 'done':
        raise HTTPException(409, 'Wait for transcription to finish.')
    folder = DATA / job_id
    with lock:
        details = make_score(json.loads((folder / 'events.json').read_text()), folder, options.bpm, options.meter, options.split, options.feel)
        jobs[job_id]['details'] = details
    return get_job(job_id)

@app.get('/api/jobs/{job_id}/files/{name}')
def download(job_id: str, name: str):
    if get_job(job_id)['status'] != 'done':
        raise HTTPException(409, 'Wait for transcription to finish.')
    if name not in ('performance.mid', 'score.musicxml', 'events.json', 'performance.wav', 'score.wav', 'score-events.json'):
        raise HTTPException(404)
    if not (DATA / job_id / name).is_file():
        raise HTTPException(404, 'Rebuild the notation to create playback files.')
    return FileResponse(DATA / job_id / name, filename=name)

@app.get('/api/jobs/{job_id}/workshop')
def workshop_read(job_id: str):
    if get_job(job_id)['status']!='done':raise HTTPException(409,'Finish transcription first.')
    with lock:return read_document(DATA/job_id)

@app.put('/api/jobs/{job_id}/workshop')
def workshop_save(job_id: str, document: EditDocument):
    if get_job(job_id)['status']!='done':raise HTTPException(409,'Finish transcription first.')
    with lock:
        try:return save_document(DATA/job_id,document)
        except ValueError as exc:raise HTTPException(409,str(exc))

@app.get('/api/jobs/{job_id}/workshop/files/{name}')
def workshop_file(job_id: str,name: str):
    get_job(job_id)
    if name not in ('score.musicxml','score.wav','score-events.json'):raise HTTPException(404)
    with lock:
        document=read_document(DATA/job_id)
        folder=DATA/job_id
        if not document['revision'].startswith('base-'):folder=folder/'workshop'/document['revision']
    return FileResponse(folder/name,filename=name)

for details_file in sorted(DATA.glob('*/details.json'), key=lambda p: p.stat().st_mtime):
    try:
        folder = details_file.parent
        events = json.loads((folder / 'events.json').read_text())
        jobs[folder.name] = {'id':folder.name, 'status':'done', 'message':'Saved transcription restored.',
            'details':json.loads(details_file.read_text()), 'note_count':len(events['notes']),
            'pedal_count':len(events['pedals']), 'duration':events['duration']}
    except (OSError, ValueError, KeyError):
        logging.warning('Skipping incomplete saved job: %s', details_file.parent.name)

app.mount('/', StaticFiles(directory=ROOT / 'dist', html=True), name='web')
