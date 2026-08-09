"""Deterministic Phase 3 semantic choreography (additive to phrase_grid v1)."""
from __future__ import annotations
import hashlib, json
from typing import Any

SCHEMA="neon_music.movement_events.v1"; LIB_SCHEMA="neon_music.movement_library.v2"; PLAN_SCHEMA="neon_music.choreography_plan.v2"
WEIGHTS={"music_alignment":.17,"phrase_coherence":.18,"teachability":.14,"transition_quality":.12,"left_right_balance":.08,"section_fit":.10,"energy_fit":.07,"novelty":.04,"callback_quality":.04,"fatigue_safety":.04,"visual_readability":.02}
def _m(i,n,c,side="center",intensity=.25,durations=(2,4),prep=2,recovery=0,level="standing",travel="none",space="center",fatigue="legs_light",mirror=None,cue="HOLD_RING",prev=(),nxt=(),tags=("beginner",)):
 return {"id":i,"display_name":n,"category":c,"side":side,"difficulty":1,"intensity":intensity,"duration_beats":list(durations),"preparation_beats":prep,"recovery_beats":recovery,"body_level":level,"travel":travel,"required_space":space,"fatigue_group":fatigue,"mirror_id":mirror or i,"allowed_previous":[],"forbidden_previous":list(prev),"allowed_next":[],"forbidden_next":list(nxt),"max_repeats":4,"preferred_sections":["intro","verse","build","chorus","drop","breakdown","outro"],"preferred_accents":["beat","downbeat"],"cue_archetype":cue,"tags":list(tags)}
MOVEMENT_LIBRARY={
"IDLE_BOUNCE":_m("IDLE_BOUNCE","Idle Bounce","base_groove",intensity=.15,durations=(4,8),cue="HOLD_RING"),"MARCH":_m("MARCH","March","locomotion",intensity=.22,durations=(4,8),cue="ALTERNATING_FOOT_PULSES"),
"STEP_LEFT":_m("STEP_LEFT","Step Left","locomotion","left",.30,travel="left",space="left",mirror="STEP_RIGHT",cue="LANE_STEP_LEFT",tags=("beginner","side_step")),"STEP_RIGHT":_m("STEP_RIGHT","Step Right","locomotion","right",.30,travel="right",space="right",mirror="STEP_LEFT",cue="LANE_STEP_RIGHT",tags=("beginner","side_step")),
"DOUBLE_STEP_LEFT":_m("DOUBLE_STEP_LEFT","Double Step Left","locomotion","left",.40,(4,),travel="left",space="left",mirror="DOUBLE_STEP_RIGHT",cue="LANE_DOUBLE_STEP_LEFT"),"DOUBLE_STEP_RIGHT":_m("DOUBLE_STEP_RIGHT","Double Step Right","locomotion","right",.40,(4,),travel="right",space="right",mirror="DOUBLE_STEP_LEFT",cue="LANE_DOUBLE_STEP_RIGHT"),
"STEP_TOUCH_LEFT":_m("STEP_TOUCH_LEFT","Step Touch Left","locomotion","left",.32,mirror="STEP_TOUCH_RIGHT",cue="FOOT_PAD_LEFT"),"STEP_TOUCH_RIGHT":_m("STEP_TOUCH_RIGHT","Step Touch Right","locomotion","right",.32,mirror="STEP_TOUCH_LEFT",cue="FOOT_PAD_RIGHT"),
"LEAN_LEFT":_m("LEAN_LEFT","Lean Left","core","left",.28,fatigue="core",mirror="LEAN_RIGHT",cue="SIDE_SWEEP_FROM_RIGHT",nxt=("LEAN_RIGHT",)),"LEAN_RIGHT":_m("LEAN_RIGHT","Lean Right","core","right",.28,fatigue="core",mirror="LEAN_LEFT",cue="SIDE_SWEEP_FROM_LEFT",nxt=("LEAN_LEFT",)),
"SIDE_REACH_LEFT":_m("SIDE_REACH_LEFT","Side Reach Left","upper_body","left",.30,fatigue="upper_body",mirror="SIDE_REACH_RIGHT",cue="HAND_TARGET_LEFT"),"SIDE_REACH_RIGHT":_m("SIDE_REACH_RIGHT","Side Reach Right","upper_body","right",.30,fatigue="upper_body",mirror="SIDE_REACH_LEFT",cue="HAND_TARGET_RIGHT"),
"SQUAT":_m("SQUAT","Squat","legs",intensity=.62,prep=4,recovery=2,level="low",fatigue="legs_heavy",cue="OVERHEAD_BAR",nxt=("JUMP",)),"DUCK":_m("DUCK","Duck","core",intensity=.48,prep=4,recovery=2,level="low",fatigue="legs_heavy",cue="LOW_CLEARANCE_GATE",prev=("JUMP",)),
"SMALL_JUMP":_m("SMALL_JUMP","Small Jump","jump",intensity=.62,durations=(2,),prep=4,recovery=2,fatigue="cardio",cue="FLOOR_PULSE_SMALL"),"JUMP":_m("JUMP","Jump","jump",intensity=.82,durations=(2,),prep=4,recovery=4,fatigue="cardio",cue="FLOOR_PULSE_LARGE",prev=("SQUAT",),nxt=("DUCK",)),
"PUNCH_LEFT":_m("PUNCH_LEFT","Punch Left","upper_body","left",.38,(2,),fatigue="upper_body",mirror="PUNCH_RIGHT",cue="HAND_TARGET_LEFT"),"PUNCH_RIGHT":_m("PUNCH_RIGHT","Punch Right","upper_body","right",.38,(2,),fatigue="upper_body",mirror="PUNCH_LEFT",cue="HAND_TARGET_RIGHT"),
"DOUBLE_PUNCH":_m("DOUBLE_PUNCH","Double Punch","upper_body",intensity=.48,fatigue="upper_body",cue="HAND_TARGET_DOUBLE"),"CLAP":_m("CLAP","Clap","upper_body",intensity=.25,fatigue="upper_body",cue="CENTER_CONVERGE_TARGETS"),"OPEN_ARMS":_m("OPEN_ARMS","Open Arms","upper_body",intensity=.24,durations=(4,),fatigue="upper_body",cue="OUTWARD_EXPAND_TARGETS"),
"RUN_IN_PLACE":_m("RUN_IN_PLACE","Run In Place","cardio",intensity=.70,durations=(4,8),fatigue="cardio",cue="ALTERNATING_FOOT_PULSES"),"HIGH_KNEES":_m("HIGH_KNEES","High Knees","cardio",intensity=.78,durations=(4,8),fatigue="cardio",cue="HIGH_FOOT_PULSES"),"FREEZE":_m("FREEZE","Freeze","phrase_control",intensity=.08,durations=(2,4,8),fatigue="core",cue="HOLD_RING"),"POSE":_m("POSE","Pose","phrase_control",intensity=.12,durations=(4,8),cue="POSE_FRAME")}
ALIASES={"MARCH_IN_PLACE":"MARCH","BOUNCE":"IDLE_BOUNCE","ARMS_OPEN":"OPEN_ARMS","BASE_RECOVERY":"IDLE_BOUNCE"}
def _b(role,*items): return {"role":role,"events":[{"movement":m,"duration_beats":d} for m,d in items]}
def _pattern(role,pindex,variant):
 if pindex<=0 or role=="intro":
  a="STEP_LEFT" if variant%2==0 else "STEP_TOUCH_LEFT"; r=MOVEMENT_LIBRARY[a]["mirror_id"]; return "TEACH_REPEAT_MIRROR_COMBINE",[_b("TEACH",(a,4),(a,4)),_b("REPEAT",(a,4),(r,4)),_b("MIRROR",(r,4),(r,4)),_b("COMBINE",(a,2),(r,2),(a,2),(r,2))]
 if role in {"chorus","drop","outro"}:
  base=(("STEP_TOUCH_LEFT",2),("PUNCH_RIGHT",2),("STEP_TOUCH_RIGHT",2),("PUNCH_LEFT",2))
  variations=[
   base,
   (("RUN_IN_PLACE",4),("DOUBLE_PUNCH",4)),
   (("HIGH_KNEES",4),("CLAP",2),("DOUBLE_PUNCH",2)),
   (("SMALL_JUMP",2),("PUNCH_LEFT",2),("PUNCH_RIGHT",2),("POSE",2)),
  ]
  variation=variations[variant%4];mirror=tuple((MOVEMENT_LIBRARY[m]["mirror_id"],d) for m,d in variation)
  signature=(("SQUAT",4),("DOUBLE_PUNCH",2),("CLAP",2)) if role=="chorus" else (("STEP_TOUCH_LEFT",2),("DOUBLE_PUNCH",2),("STEP_TOUCH_RIGHT",2),("POSE" if role=="outro" else "CLAP",2))
  return "CALLBACK_VARIATION_MIRROR_SIGNATURE",[_b("CALLBACK",*base),_b("VARIATION",*variation),_b("MIRROR",*mirror),_b("SIGNATURE",*signature)]
 if role=="build":
  endings=[
   (("STEP_LEFT",2),("PUNCH_LEFT",2),("STEP_RIGHT",2),("DOUBLE_PUNCH",2)),
   (("RUN_IN_PLACE",4),("PUNCH_LEFT",2),("PUNCH_RIGHT",2)),
   (("HIGH_KNEES",4),("DOUBLE_PUNCH",2),("CLAP",2)),
   (("SMALL_JUMP",2),("STEP_LEFT",2),("STEP_RIGHT",2),("DOUBLE_PUNCH",2)),
  ]
  return "BUILD",[_b("REPEAT",("STEP_TOUCH_LEFT",4),("STEP_TOUCH_RIGHT",4)),_b("ALTERNATE",("PUNCH_LEFT",2),("PUNCH_RIGHT",2),("PUNCH_LEFT",2),("PUNCH_RIGHT",2)),_b("COMBINE",("STEP_TOUCH_LEFT",2),("PUNCH_LEFT",2),("STEP_TOUCH_RIGHT",2),("PUNCH_RIGHT",2)),_b("BUILD",*endings[variant%4])]
 if role=="breakdown":
  recoveries=[
   [_b("RECOVERY",("MARCH",8)),_b("RECOVERY",("IDLE_BOUNCE",8)),_b("RECOVERY",("OPEN_ARMS",4),("FREEZE",4)),_b("RECOVERY",("MARCH",4),("POSE",4))],
   [_b("RECOVERY",("LEAN_LEFT",4),("SIDE_REACH_LEFT",4)),_b("RECOVERY",("LEAN_RIGHT",4),("SIDE_REACH_RIGHT",4)),_b("RECOVERY",("OPEN_ARMS",4),("IDLE_BOUNCE",4)),_b("RECOVERY",("MARCH",4),("FREEZE",4))],
   [_b("RECOVERY",("STEP_TOUCH_LEFT",4),("STEP_TOUCH_RIGHT",4)),_b("RECOVERY",("OPEN_ARMS",4),("CLAP",4)),_b("RECOVERY",("MARCH",8)),_b("RECOVERY",("FREEZE",4),("POSE",4))],
   [_b("RECOVERY",("IDLE_BOUNCE",8)),_b("RECOVERY",("SIDE_REACH_LEFT",4),("SIDE_REACH_RIGHT",4)),_b("RECOVERY",("MARCH",8)),_b("RECOVERY",("OPEN_ARMS",4),("POSE",4))],
  ]
  return "RECOVERY",recoveries[variant%4]
 pairs=[("STEP_TOUCH_LEFT","PUNCH_LEFT"),("STEP_LEFT","SIDE_REACH_LEFT"),("LEAN_LEFT","SIDE_REACH_LEFT"),("DOUBLE_STEP_LEFT","CLAP")]
 a,b=pairs[variant%4];ar=MOVEMENT_LIBRARY[a]["mirror_id"];br=MOVEMENT_LIBRARY[b]["mirror_id"];return "REPEAT_ALTERNATE_MIRROR_COMBINE",[_b("REPEAT",(a,4),(ar,4)),_b("ALTERNATE",(a,2),(b,2),(a,2),(b,2)),_b("MIRROR",(ar,2),(br,2),(ar,2),(br,2)),_b("COMBINE",(a,2),(b,2),(ar,2),(br,2))]
def _role(phrase,pos,count):
 raw=str(phrase.get("section_role",phrase.get("section_id",""))).lower()
 for token,value in (("intro","intro"),("build","build"),("chorus","chorus"),("drop","drop"),("break","breakdown"),("outro","outro")):
  if token in raw:return value
 r=pos/max(1,count-1)
 return "intro" if r<.1 else "build" if r<.44 and r>=.30 else "chorus" if (.44<=r<.62 or .72<=r<.90) else "breakdown" if .62<=r<.72 else "outro" if r>=.90 else "verse"
def _flat(p):return [e for b in p for e in b["events"]]
def _balance(events):
 l=sum(MOVEMENT_LIBRARY[e["movement"]]["intensity"]*e["duration_beats"] for e in events if MOVEMENT_LIBRARY[e["movement"]]["side"]=="left");r=sum(MOVEMENT_LIBRARY[e["movement"]]["intensity"]*e["duration_beats"] for e in events if MOVEMENT_LIBRARY[e["movement"]]["side"]=="right");t=l+r;return {"left_load":round(l,3),"right_load":round(r,3),"difference_ratio":round(abs(l-r)/t if t else 0,4)}
def _violations(patterns,difficulty):
 f=_flat(patterns);out=[]
 if any(sum(e["duration_beats"] for e in b["events"])!=8 for b in patterns):out.append("eight_count_duration_mismatch")
 if sum(e["movement"] in {"JUMP","SMALL_JUMP"} for e in f)>{"beginner":2,"normal":4,"advanced":6}.get(difficulty,4):out.append("jump_limit_exceeded")
 for a,b in zip(f,f[1:]):
  if b["movement"] in MOVEMENT_LIBRARY[a["movement"]]["forbidden_next"] or a["movement"] in MOVEMENT_LIBRARY[b["movement"]]["forbidden_previous"]:out.append(f"forbidden_transition:{a['movement']}->{b['movement']}")
 if _balance(f)["difference_ratio"]>.20:out.append("left_right_imbalance")
 return sorted(set(out))
def _metrics(patterns,role,learned,pindex,targets=None):
 targets=targets or {};f=_flat(patterns);u={e["movement"] for e in f};new=u-learned;bal=_balance(f)
 target_intensity=float(targets.get("intensity",.42));target_complexity=float(targets.get("complexity",.3));accent_curve=[float(v) for v in targets.get("accent_curve",[]) if isinstance(v,(int,float))]
 cursor=0;starts=[];loads=[];families=[];categories=[];high_impact=0
 for event in f:
  meta=MOVEMENT_LIBRARY[event["movement"]];starts.append(cursor);loads.append(float(meta["intensity"]));families.append(str(meta["fatigue_group"]));categories.append(str(meta["category"]));cursor+=int(event["duration_beats"])
  if event["movement"] in {"JUMP","SMALL_JUMP","HIGH_KNEES","RUN_IN_PLACE"}:high_impact+=int(event["duration_beats"])
 if accent_curve and starts:
  sampled=[accent_curve[min(len(accent_curve)-1,max(0,start))] for start in starts];baseline=sum(accent_curve)/len(accent_curve);alignment=sum(sampled)/len(sampled)
  music_alignment=max(0,min(1,.35+.65*(alignment-baseline+0.5)))
 else:music_alignment=.72+min(.16,sum(start%4==0 for start in starts)/max(1,len(starts))*.16)
 mean_intensity=sum(loads)/max(1,len(loads));energy_fit=max(0,1-abs(mean_intensity-target_intensity)/.55)
 transitions=sum(a!=b for a,b in zip(categories,categories[1:]));transition_quality=max(0,1-.08*sum(b in MOVEMENT_LIBRARY[a]["forbidden_next"] for a,b in zip([e["movement"] for e in f],[e["movement"] for e in f][1:])))
 phrase_coherence=max(0,min(1,.72+.05*len(patterns)-.025*max(0,transitions-5)))
 preferred={"intro":{"base_groove","locomotion"},"verse":{"locomotion","upper_body","core"},"bridge":{"upper_body","core","phrase_control"},"build":{"locomotion","upper_body","cardio"},"chorus":{"locomotion","upper_body","cardio","jump"},"drop":{"cardio","jump","upper_body"},"breakdown":{"base_groove","core","upper_body","phrase_control"},"outro":{"phrase_control","upper_body","locomotion"}}.get(role,set(categories))
 section_fit=sum(category in preferred for category in categories)/max(1,len(categories))
 actual_complexity=min(1,(len(set(categories))-.5)/4+transitions/max(1,len(categories))*0.45);complexity_fit=max(0,1-abs(actual_complexity-target_complexity)/.7)
 fatigue_safety=max(0,1-high_impact/48-max(0,mean_intensity-target_intensity)*.35)
 sides={MOVEMENT_LIBRARY[event["movement"]]["side"] for event in f};side_score=1-bal["difference_ratio"] if {"left","right"}<=sides else .55 if not ({"left","right"}&sides) else .25
 return {"music_alignment":round(music_alignment,6),"phrase_coherence":round(phrase_coherence,6),"teachability":round(max(0,1-max(0,len(new)-1)*.30),6),"transition_quality":round(transition_quality,6),"left_right_balance":round(side_score,6),"section_fit":round(section_fit,6),"energy_fit":round(energy_fit,6),"novelty":round(min(1,.35+.13*len(new)+.25*complexity_fit),6),"callback_quality":1.0 if role in {"chorus","drop","outro"} and pindex>0 else .62,"fatigue_safety":round(fatigue_safety,6),"visual_readability":round(max(.35,1-.08*max(0,len(set(categories))-4)),6)}
def _fatigue(events):
 d={k:0.0 for k in ("legs_light","legs_heavy","cardio","upper_body","core")}
 for e in events:d[e["fatigue_group"]]+=e["intensity"]*e["duration_beats"]
 return {k:round(v,3) for k,v in d.items()}
def build_plan(timing,grid,cfg):
 interval=max(.001,float(timing.get("beat_interval",.5)));duration=float(timing.get("duration",0));phrases=grid.get("phrases",[]);learned={"MARCH","IDLE_BOUNCE","OPEN_ARMS"};events=[];debug=[];ei=0;movement_use={};recent_signatures=[]
 beat_time={int(beat.get("index",0)):float(beat.get("time",0)) for beat in timing.get("beat_grid",[]) if isinstance(beat,dict)}
 beat_music={int(beat.get("index",0)):beat for beat in timing.get("beat_features",[]) if isinstance(beat,dict)}
 def time_at(index,fallback):return beat_time.get(index,fallback)
 for pos,p in enumerate(phrases):
  if not p.get("count8_blocks") or int(p.get("index",pos))<0:continue
  pi=int(p.get("index",pos));role=_role(p,pos,len(phrases));cands=[]
  targets=dict(p.get("section_movement_targets",{}) if isinstance(p.get("section_movement_targets"),dict) else {})
  targets.update(p.get("music_targets",{}) if isinstance(p.get("music_targets"),dict) else {})
  for ci in range(max(8,int(cfg.get("candidate_count",8)))):
   template,patterns=_pattern(role,pi,ci%4);viol=_violations(patterns,str(cfg.get("difficulty","normal")));metrics=_metrics(patterns,role,learned,pi,targets);flat=_flat(patterns);signature=tuple((item["movement"],item["duration_beats"]) for item in flat);variety=sum(1/(1+movement_use.get(item["movement"],0)) for item in flat)/max(1,len(flat));repeat_penalty=.07 if signature in recent_signatures[-3:] else 0;score=round(sum(metrics[k]*WEIGHTS[k] for k in WEIGHTS)+.035*variety-repeat_penalty,6);cands.append({"candidate":ci,"template":template,"patterns":patterns,"metrics":metrics,"score_breakdown":{**metrics,"variety_bonus":round(.035*variety,6),"recent_sequence_penalty":round(repeat_penalty,6)},"score":score,"hard_violations":viol,"sequence_signature":signature})
  valid=[c for c in cands if not c["hard_violations"]];sel=max(valid or cands,key=lambda c:(not c["hard_violations"],c["score"],-c["candidate"]));p.update({"template":sel["template"],"selected_candidate":sel["candidate"],"candidate_score":sel["score"],"section_role":role,"selected_metrics":sel["metrics"]});cursor=0;pe=[]
  recent_signatures.append(sel["sequence_signature"])
  for bi,b in enumerate(sel["patterns"]):
   if bi<len(p["count8_blocks"]):p["count8_blocks"][bi].update({"role":b["role"],"template":sel["template"],"pattern_id":f"{p['id']}_{b['role'].lower()}"})
   for item in b["events"]:
    m=item["movement"];meta=MOVEMENT_LIBRARY[m];beats=int(item["duration_beats"]);beat_index=int(p.get("start_beat_index",0))+cursor;fallback=float(p["start_time"])+cursor*interval;hit=time_at(beat_index,fallback);end=time_at(beat_index+beats,hit+beats*interval);cursor+=beats
    if hit<0 or hit>duration or end>duration+interval*.25:continue
    new=m not in learned;lead=6 if b["role"] in {"COMBINE","BUILD","SIGNATURE"} else 4 if new else max(2,meta["preparation_beats"]);instruction=max(0,min(time_at(beat_index-lead,hit-lead*interval),hit-lead*interval));pre_hit=max(instruction,min(time_at(beat_index-1,hit-interval),hit-interval));x=.34 if meta["side"]=="left" else .68 if meta["side"]=="right" else .49;music=beat_music.get(beat_index,{})
    e={"id":f"move_{ei:05d}","type":"movement","schema":SCHEMA,"movement":m,"display_name":meta["display_name"],"instruction_time":round(instruction,6),"spawn_time":round(instruction,6),"pre_hit_time":round(pre_hit,6),"hit_time":round(hit,6),"feedback_end_time":round(hit+.15,6),"despawn_time":round(max(hit+.25,end),6),"duration_beats":beats,"duration":round(max(.001,end-hit),6),"lead_beats":lead,"lead_time":round(hit-instruction,6),"phrase_id":p["id"],"phrase_index":pi,"count8_index":bi,"beat_index":beat_index,"motif_id":"signature_A" if b["role"] in {"CALLBACK","SIGNATURE"} else f"{p['id']}_motif_A","phrase_template":sel["template"],"block_role":b["role"],"side":meta["side"],"intensity":meta["intensity"],"difficulty":1,"is_new":new,"is_mirrored":meta["side"]=="right","mirror_of":meta["mirror_id"] if meta["side"]=="right" else "","cue_archetype":meta["cue_archetype"],"cue_bounds_normalized":{"left":x,"top":.18,"width":.18,"height":.64},"mandatory":True,"lifecycle":["SPAWN","PREVIEW","APPROACH","PRE_HIT","HIT","FEEDBACK","DESPAWN"],"judgment_plane":"receptor_hit_z","judgment_z":0.0,"expected_cross_time":round(hit,6),"judgment_error":0.0,"preparation_pose":"neutral","end_pose":meta["body_level"],"fatigue_group":meta["fatigue_group"],"candidate_score":sel["score"],"music_accent":float(music.get("accent",0.0)),"music_accent_type":str(music.get("accent_type","mixed")),"music_energy":float(music.get("energy",targets.get("energy",0.0))),"music_complexity":float(music.get("complexity",targets.get("complexity",0.0)))}
    events.append(e);pe.append(e);learned.add(m);movement_use[m]=movement_use.get(m,0)+1;ei+=1
  p["left_right_balance"]=_balance(pe);p["fatigue_state"]=_fatigue(pe)
  for event in pe:event.update({"section_role":role,"left_right_balance":p["left_right_balance"],"fatigue_state":p["fatigue_state"]})
  rej=[c for c in cands if c["hard_violations"]];debug.append({"phrase_id":p["id"],"section_role":role,"music_targets":targets,"selected_candidate":sel["candidate"],"selected_metrics":sel["metrics"],"candidate_scores":[{"candidate":c["candidate"],"score":c["score"],"metrics":c["metrics"],"score_breakdown":c["score_breakdown"]} for c in cands],"rejected_candidates":[c["candidate"] for c in rej],"rejection_reasons":[{"candidate":c["candidate"],"reasons":c["hard_violations"]} for c in rej]})
 return {"schema":PLAN_SCHEMA,"seed":int(cfg.get("seed",3407)),"candidate_count":max(8,int(cfg.get("candidate_count",8))),"weights":WEIGHTS,"music_aware":bool(timing.get("beat_features")),"phrase_debug":debug,"movement_events":events}
def build_movement_events(timing,phrase_grid,config=None):return build_plan(timing,phrase_grid,config or {})["movement_events"]
def _active(t,events):
 previous=None
 for e in events:
  if e["hit_time"]<=t<e["hit_time"]+e["duration"]:return e
  if e["hit_time"]<=t:previous=e
 return previous
def attach_phrase_metadata(beatmap,timing,config=None):
 import phrase_grid as base
 cfg=base.choreography_config(**(config or {}));cfg.update({"seed":int((config or {}).get("seed",3407)),"candidate_count":max(8,int((config or {}).get("candidate_count",8))),"difficulty":str((config or {}).get("difficulty","normal")),"performer_safe_zone":{"left":0.0,"top":0.0,"width":.24,"height":1.0},"gameplay_corridor":{"left":.30,"top":.08,"width":.66,"height":.84},"judgment_tolerance_seconds":.0334});grid=base.build_phrase_grid(timing,cfg);plan=build_plan(timing,grid,cfg);events=plan["movement_events"];interval=max(.001,float(timing.get("beat_interval",.5)));anchor=float(grid.get("phrase_anchor_time",0))
 canonical=[beat for beat in timing.get("beat_grid",[]) if isinstance(beat,dict)]
 for note in beatmap.get("notes",[]):
  t=float(note.get("time",0))
  if "beat_index" in note:position=int(note["beat_index"])
  elif canonical:position=int(min(canonical,key=lambda beat:abs(float(beat.get("time",0))-t)).get("index",0))
  else:position=round((t-anchor)/interval)
  pi,pb=divmod(position,32);e=_active(t,events)
  if e:
   for key in ("movement","cue_archetype","lead_beats","instruction_time","is_mirrored","judgment_plane","judgment_z","phrase_template","candidate_score"):note[key]=e[key]
   note["movement_event_id"]=e["id"]
  else:note.update({"movement":"MARCH","cue_archetype":"ALTERNATING_FOOT_PULSES","lead_beats":2,"instruction_time":round(max(0,t-2*interval),6),"is_mirrored":False,"judgment_plane":"receptor_hit_z","judgment_z":0.0})
  note.update({"hit_time":round(t,6),"phrase_id":f"phrase_{pi:03d}","phrase_beat":pb,"count8_index":pb//8})
 library={"schema":LIB_SCHEMA,"movements":MOVEMENT_LIBRARY,"aliases":ALIASES}
 for d in (beatmap,timing):d.update({"choreography_config":cfg,"phrase_grid":grid,"movement_library":library,"movement_events":events,"choreography_plan":plan})
 return beatmap,timing
def deterministic_digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
