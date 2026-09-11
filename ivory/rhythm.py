"""Musical-intent heuristics, isolated from acoustic events and MIDI."""
import statistics

def infer_tempo(events):
    base = max(20, min(300, events.get('estimated_bpm') or 120))
    attacks = sorted({round(n['onset_time'], 2) for n in events['notes']})
    if len(attacks) < 4:
        return base
    # Refine within the beat tracker's tempo neighborhood, not an arbitrary new meter.
    origin = attacks[0] if attacks[0] < .2 else 0
    def cost(bpm):
        errors = [min(abs((t-origin)*bpm/60*2-round((t-origin)*bpm/60*2))/2,.15)**2 for t in attacks]
        return statistics.mean(errors) + .3*((bpm-base)/base)**2
    candidates = [round(base*.94+i*.1,1) for i in range(int(base*.12/.1)+1)]
    return min((b for b in candidates if 20<=b<=300),key=cost)

def interpret(notes,bpm,mode='expressive'):
    grid = {'precise':.125,'expressive':.25,'simple':.5}[mode]
    tolerance = {'precise':0,'expressive':min(.09,60/bpm*.12),'simple':min(.12,60/bpm*.18)}[mode]
    ordered = sorted(notes,key=lambda n:n['onset_time'])
    clusters=[]
    for n in ordered:
        if (clusters and n['onset_time']-clusters[-1][0]['onset_time']<=tolerance
                and n['midi_note'] not in {x['midi_note'] for x in clusters[-1]}):
            clusters[-1].append(n)
        else:
            clusters.append([n])
    result=[]
    for group in clusters:
        onset=statistics.median(n['onset_time'] for n in group)
        start=round(onset*bpm/60/grid)*grid
        # Distinct attacks that collide on a grid must not erase repeated notes.
        if result and start<=result[-1][0]:
            start=result[-1][0]+grid
        result.append((start,group))
    return result,grid
