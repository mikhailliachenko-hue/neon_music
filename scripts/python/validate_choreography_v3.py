#!/usr/bin/env python3
"""Phase 3/4 validator with phrase/timecode diagnostics and JSON report."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(PROJECT/'scripts'/'python'))
from choreography_v3 import MOVEMENT_LIBRARY, deterministic_digest

def overlap(a,b): return a['left']<b['left']+b['width'] and a['left']+a['width']>b['left'] and a['top']<b['top']+b['height'] and a['top']+a['height']>b['top']
def issue(level,code,e,msg): return {'level':level,'code':code,'timecode':round(float(e.get('hit_time',0)),3),'phrase_id':str(e.get('phrase_id','')),'movement_id':str(e.get('id','')),'message':msg}
def validate(beatmap,timing):
 errors=[];warnings=[];events=timing.get('movement_events',[]);cfg=timing.get('choreography_config',{});safe=cfg.get('performer_safe_zone',{'left':0,'top':0,'width':.24,'height':1});cue_doc=json.loads((PROJECT/'data'/'obstacle_cue_mapping_v2.json').read_text(encoding='utf-8-sig')); mappings=cue_doc['mappings']; known_cues=set(cue_doc['archetypes'])
 for mid,meta in MOVEMENT_LIBRARY.items():
  if meta['mirror_id'] not in MOVEMENT_LIBRARY: errors.append(issue('hard','missing_mirror_id',{},f'{mid} mirror {meta["mirror_id"]} is unknown'))
 for i,e in enumerate(events):
  m=e.get('movement'); cue=e.get('cue_archetype'); meta=MOVEMENT_LIBRARY.get(m)
  if not meta: errors.append(issue('hard','unknown_movement_id',e,f'Unknown movement {m}'));continue
  if cue not in known_cues: errors.append(issue('hard','unknown_cue_archetype',e,f'Unknown cue {cue}'))
  if mappings.get(m)!=cue: errors.append(issue('hard','movement_cue_mismatch',e,f'{m} must map to {mappings.get(m)}'))
  if e.get('mandatory',True) and overlap(e.get('cue_bounds_normalized',{}),safe): errors.append(issue('hard','mandatory_cue_safe_zone_overlap',e,'Mandatory cue overlaps performer safe zone'))
  if abs(float(e.get('expected_cross_time',e.get('hit_time',0)))-float(e.get('hit_time',0)))>.0334 or abs(float(e.get('judgment_error',0)))>.0334: errors.append(issue('hard','judgment_timing',e,'Cue crosses judgment plane outside one frame'))
  required=6 if e.get('block_role') in {'COMBINE','BUILD','SIGNATURE'} else 4 if e.get('is_new') else max(2,int(meta['preparation_beats']))
  actual=float(e.get('lead_time',0))/max(.001,float(timing.get('beat_interval',.5)))
  if actual+1e-3<required and float(e.get('hit_time',0))>=required*float(timing.get('beat_interval',.5)): errors.append(issue('hard','lead_time_too_short',e,f'lead={actual:.2f}, required={required} beats'))
  if i:
   prev=events[i-1]; pm=prev.get('movement');
   if m in MOVEMENT_LIBRARY.get(pm,{}).get('forbidden_next',[]) or pm in meta.get('forbidden_previous',[]): errors.append(issue('hard','impossible_transition',e,f'{pm} -> {m}'))
 phrases={p['id']:p for p in timing.get('phrase_grid',{}).get('phrases',[]) if isinstance(p,dict)}
 for pid,p in phrases.items():
  pe=[e for e in events if e.get('phrase_id')==pid]
  if not pe: continue
  jumps=sum(e['movement'] in {'JUMP','SMALL_JUMP'} for e in pe); limit={'beginner':2,'normal':4,'advanced':6}.get(cfg.get('difficulty','normal'),4)
  if jumps>limit: errors.append(issue('hard','jump_limit_exceeded',pe[0],f'{jumps}>{limit}'))
  for half in (pe[:len(pe)//2],pe[len(pe)//2:]):
   if sum(e['movement']=='SQUAT' for e in half)>2: errors.append(issue('hard','squat_limit_exceeded',half[0],'More than two squats per 16 beats'))
  sides={e['side'] for e in pe}; bal=p.get('left_right_balance',{}).get('difference_ratio',0)
  if 'left' not in sides or 'right' not in sides: warnings.append(issue('warning','missing_mirror',pe[0],'Phrase has no left/right mirrored material'))
  if bal>.20: warnings.append(issue('warning','side_asymmetry',pe[0],f'balance difference {bal:.1%}'))
  if len({e['movement'] for e in pe})<2: warnings.append(issue('warning','monotonous_phrase',pe[0],'32-count phrase is too monotonous'))
 one=sum(e.get('duration_beats')==1 for e in events); ratio=sum(2<=int(e.get('duration_beats',0))<=8 for e in events)/max(1,len(events))
 if one/ max(1,len(events))>.20: warnings.append(issue('warning','too_many_one_beat_movements',{},f'{one} one-beat events'))
 report={'schema':'neon_music.choreography_validation.v2','valid':not errors,'summary':{'hard_errors':len(errors),'warnings':len(warnings),'movement_events':len(events),'phrases':len(phrases),'duration_2_to_8_ratio':round(ratio,4),'mandatory_cue_safe_zone_overlap':sum(x['code']=='mandatory_cue_safe_zone_overlap' for x in errors),'max_judgment_error_seconds':max([abs(float(e.get('judgment_error',0))) for e in events] or [0]),'deterministic_digest':deterministic_digest({'phrase_grid':timing.get('phrase_grid'),'movement_events':events,'choreography_plan':timing.get('choreography_plan')})},'hard_errors':errors,'warnings':warnings}
 return report

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--beatmap',type=Path,default=PROJECT/'output'/'beatmap.json');ap.add_argument('--metadata',type=Path,default=PROJECT/'output'/'beat_grid.json');ap.add_argument('--report',type=Path,default=PROJECT/'output'/'reports'/'choreography_validation_v3.json');args=ap.parse_args();beatmap=json.loads(args.beatmap.read_text(encoding='utf-8-sig'));timing=json.loads(args.metadata.read_text(encoding='utf-8-sig'));report=validate(beatmap,timing);args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report['summary'],ensure_ascii=False));return 0 if report['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
