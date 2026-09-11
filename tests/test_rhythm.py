from ivory.rhythm import interpret, infer_tempo
from ivory.notation import spelled
from music21 import key

def n(p,t): return {'midi_note':p,'onset_time':t,'offset_time':t+1}

def test_loose_chord_across_grid_boundary():
    groups,grid=interpret([n(60,.105),n(64,.15),n(67,.18)],60)
    assert len(groups)==1 and len(groups[0][1])==3

def test_repeated_notes_and_arpeggios_survive():
    groups,_=interpret([n(60,0),n(60,.06),n(64,.2)],60)
    assert len(groups)==3
    groups,_=interpret([n(60,0),n(64,.08),n(67,.16)],60)
    assert len(groups)==2  # Cluster span is bounded; no chained merge.

def test_precise_retains_separate_ornaments():
    assert len(interpret([n(60,0),n(64,.07)],60,'precise')[0])==2

def test_tempo_refines_nearby_estimate():
    events={'estimated_bpm':63,'notes':[n(60+i%5,i*60/65) for i in range(40)]}
    assert abs(infer_tempo(events)-65)<.3

def test_spelling_respects_signature_without_changing_pitch():
    assert spelled(71,key.KeySignature(-7)).name=='C-'
    for sharps in range(-7,8):
        for midi in range(21,109):
            assert spelled(midi,key.KeySignature(sharps)).midi==midi
