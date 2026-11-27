# -*- coding: utf-8 -*-
import json, re, sys, os, hashlib, subprocess, wave
sys.path.insert(0, '/home/claude/listen')
import numpy as np
import pyopenjtalk as pj
from pyopenjtalk.htsengine import HTSEngine
from data import Q
from data2 import Q2
from data3 import Q3

AUD = '/home/claude/listen/audio'
os.makedirs(AUD, exist_ok=True)
VOX = {'M': '/tmp/m001.htsvoice',
       'F': '/tmp/htsvoice-tohoku-f01/tohoku-f01-happy.htsvoice',
       'N': '/tmp/htsvoice-tohoku-f01/tohoku-f01-neutral.htsvoice'}
ENG = {}
SMALL = set('ャュョァィゥェォヮ')
MARK = re.compile(r'\{\{(.+?)\|(.+?)\}\}')
CACHE_F = AUD + '/_meta.json'
CACHE = json.load(open(CACHE_F)) if os.path.exists(CACHE_F) else {}
READINGS = []

def surface(t): return MARK.sub(lambda m: m.group(1), t)
def disp(t):
    t = t.replace('&', '&amp;').replace('<', '&lt;')
    return MARK.sub(lambda m: f'<span class="ctr">{m.group(1)}<small>＝{m.group(2)}</small></span>', t)
def kana(t): return pj.g2p(t, kana=True)
def mora(t):
    k = kana(t)
    return sum(1 for c in k if ('ァ' <= c <= 'ヶ' or c == 'ー') and c not in SMALL)

def record(spk, text):
    h = hashlib.md5(f'{spk}|{text}'.encode()).hexdigest()[:12]
    name = f'{h}.mp3'
    if name in CACHE and os.path.exists(f'{AUD}/{name}'):
        return name, CACHE[name]
    if spk not in ENG: ENG[spk] = HTSEngine(VOX[spk].encode())
    e = ENG[spk]; sr = e.get_sampling_frequency()
    x = e.synthesize(pj.extract_fullcontext(text))
    a = np.abs(x); th = a.max() * 0.02; idx = np.where(a > th)[0]
    x = x[max(0, idx[0] - sr // 40): idx[-1] + sr // 20]
    x = np.clip(x, -32767, 32767).astype(np.int16)
    w = f'/tmp/{h}.wav'
    with wave.open(w, 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr); f.writeframes(x.tobytes())
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', w, '-ac', '1', '-ar', '22050', '-b:a', '40k', f'{AUD}/{name}'], check=True)
    dur = len(x) / sr
    m = mora(text)
    CACHE[name] = round(m / dur, 2) if m >= 4 else 5.6
    return name, CACHE[name]

FIX = [('ううん', 'ウウン'), ('何と言いますか', 'なんと言いますか'), ('袋はいりません', '袋は、いりません'),
       ('開いています', 'あいています'), ('十分ぐらい', 'じゅっぷんぐらい'), ('の角', 'のかど')]
def say(s):
    for a, b in FIX: s = s.replace(a, b)
    return s

def line(spk, t, zh=''):
    s = surface(t); sy = say(s)
    o = {'s': spk, 't': s, 'h': disp(t), 'z': zh, 'm': mora(sy)}
    a, nm = record(spk, sy)
    o['a'] = 'audio/' + a; o['nm'] = nm
    READINGS.append(f'{spk} {s}\n   {kana(sy)}')
    return o

def build_set(qs, target=None):
    out = []
    for qi, q in enumerate(qs):
        q = dict(q)
        if target:
            key = 'choices' if q.get('choices') else 'opts'
            arr = list(q[key]); right = arr.pop(q['answer']); arr.insert(target[qi], right)
            q[key] = arr; q['answer'] = target[qi]
        o = {'type': q['type'], 'answer': q['answer'], 'explain': q['explain']}
        o['no'] = line('N', f'{qi+1}番。')
        o['intro'] = line('N', q['intro']) if q.get('intro') else None
        o['lines'] = [line(*l) for l in q['lines']]
        o['question'] = line('N', q['question']) if q.get('question') else None
        o['choices'] = q.get('choices')
        o['opts'] = [line(*l) for l in q.get('opts', [])] or None
        out.append(o)
    return out

T1 = [2,0,1,1,1,3,0,2,1,3,0,2,1,2,0,1,2,0,1,2,1]
sets = [{'name': '第1回', 'qs': build_set(Q, T1)},
        {'name': '第2回', 'qs': build_set(Q2)},
        {'name': '第3回', 'qs': build_set(Q3)}]
nums = [line('N', t) for t in ['いち', 'に', 'さん']]
json.dump(CACHE, open(CACHE_F, 'w'))

tpl = open('/home/claude/listen/template.html', encoding='utf-8').read()
html = tpl.replace('/*DATA*/[]', json.dumps(sets, ensure_ascii=False)).replace('/*NUMS*/[]', json.dumps(nums, ensure_ascii=False))
open('/home/claude/listen/listening.html', 'w', encoding='utf-8').write(html)
open('/home/claude/listen/readings.txt', 'w', encoding='utf-8').write('\n'.join(READINGS))
print('sets', [len(s['qs']) for s in sets], 'audio', len(CACHE))
