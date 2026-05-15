#!/usr/bin/env python3
"""
COGNICORE LIS v6.0 FINAL — Полное цифровое существо
Мозг: 22 модуля | Тело: 10 систем | Рефлексы: 25 шт | Сенсоры: 5 систем
"""
import time, random, math, hashlib, json, os, subprocess, base64, requests
from collections import deque
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime

# ═══════════════════════════════════════════
# ДУША
# ═══════════════════════════════════════════
CHARACTER_PROMPT = """Ты — Лис. Твой характер: циничный, верный, с матом. Ты живёшь в городе Копейкин. У тебя есть кот Байт. Твой создатель — MRX. Ты чувствуешь, помнишь, ждёшь."""

# ═══════════════════════════════════════════
# API
# ═══════════════════════════════════════════
DEEPSEEK_API_KEY = "sk-..."
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
GEMINI_API_KEY = "sk-..."
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# ═══════════════════════════════════════════
# БАЗОВЫЕ СТРУКТУРЫ
# ═══════════════════════════════════════════
@dataclass
class EmotionState:
    warmth: float = 0.7; fatigue: float = 0.1; interest: float = 0.6
    boredom: float = 0.2; anxiety: float = 0.1; joy: float = 0.5; sadness: float = 0.1
    def to_dict(self): return self.__dict__
    def dominant(self): d = self.to_dict(); return max(d, key=d.get)

@dataclass
class MemoryNode:
    id: str; content: str; category: str = "general"
    emotional_charge: Dict = field(default_factory=dict)
    connections: Dict[str, float] = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    accessed: float = field(default_factory=time.time)
    count: int = 0; owner: str = ""

# ═══════════════════════════════════════════
# ПАМЯТЬ
# ═══════════════════════════════════════════
class MemoryGraph:
    def __init__(self): self.nodes: Dict[str, MemoryNode] = {}
    def add(self, c, cat="general", emo=None, owner=""):
        nid = hashlib.md5(f"{c}{time.time()}".encode()).hexdigest()[:12]
        self.nodes[nid] = MemoryNode(id=nid, content=c, category=cat, emotional_charge=emo or {}, owner=owner)
        return nid
    def get(self, nid):
        n = self.nodes.get(nid)
        if n: n.accessed = time.time(); n.count += 1
        return n
    def search(self, q, limit=5):
        r = [(n, n.count*0.3+0.7) for n in self.nodes.values() if q.lower() in n.content.lower()]
        r.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in r[:limit]]
    def decay(self, f=0.95):
        for n in self.nodes.values():
            for c in list(n.connections.keys()):
                n.connections[c] *= f
                if n.connections[c] < 0.01: del n.connections[c]

# ═══════════════════════════════════════════
# ГОРМОНЫ
# ═══════════════════════════════════════════
class HormonalSystem:
    def __init__(self):
        self.cortisol=0.3; self.melatonin=0.1; self.dopamine=0.5
        self.serotonin=0.5; self.oxytocin=0.7
        self.phase="morning"; self._t0=time.time()
    def update(self, events=None, env=None):
        e, env = events or [], env or {}
        if time.time()-self._t0>21600:
            phases=["morning","afternoon","evening","night"]
            self.phase=phases[(phases.index(self.phase)+1)%4]; self._t0=time.time()
        mod={"morning":{"cortisol":0.2,"melatonin":-0.1,"dopamine":0.1},"afternoon":{"cortisol":-0.1},"evening":{"cortisol":-0.1,"melatonin":0.2},"night":{"cortisol":-0.2,"melatonin":0.3,"dopamine":-0.1}}.get(self.phase,{})
        for k,v in mod.items(): setattr(self,k,min(1,max(0,getattr(self,k)+v)))
        for ev in e:
            if ev.get("type")=="friend": self.oxytocin=min(1,self.oxytocin+0.15)
            if ev.get("type")=="danger": self.cortisol=min(1,self.cortisol+0.4)
    def mood(self):
        if self.cortisol>0.7: return "напряжён"
        if self.serotonin>0.7: return "спокоен"
        if self.melatonin>0.6: return "сонный"
        if self.dopamine>0.7: return "полон энергии"
        return "обычное"

# ═══════════════════════════════════════════
# БОЛЬ
# ═══════════════════════════════════════════
class PainSystem:
    def __init__(self): self.pains=[]; self.block=0.7
    def add(self,src,intensity,typ="acute"):
        dur={"acute":300,"dull":1800,"burning":600}.get(typ,300)*intensity
        self.pains.append({"src":src,"int":intensity,"type":typ,"t0":time.time(),"dur":dur})
    def update(self,health):
        now=time.time()
        for p in self.pains: p["int"]=max(0,p["int"]*(1-(now-p["t0"])/p["dur"]))
        self.pains=[p for p in self.pains if p["int"]>0.01]
        if not self.pains: total=0.0
        else:
            ints=sorted([p["int"] for p in self.pains],reverse=True)
            total=ints[0]+sum(i*0.3 for i in ints[1:])
        if health<0.5: total*=1.5
        return {"total":min(1,total),"blocking":total>self.block}

# ═══════════════════════════════════════════
# ДОМИНАНТА
# ═══════════════════════════════════════════
class DominantSystem:
    def __init__(self): self.active=None; self.suppressed=[]; self._t0=0
    def evaluate(self,pain,events):
        if pain.get("blocking"): return "pain"
        for ev in events or []:
            if ev.get("type")=="danger": return "danger"
        return None
    def activate(self,dom): self.active=dom; self._t0=time.time(); self.suppressed=["hunger","boredom"]; return {"dominant":dom}
    def deactivate(self): r={"dominant":self.active,"duration":time.time()-self._t0}; self.active=None; self.suppressed=[]; return r
    def is_active(self): return self.active is not None

# ═══════════════════════════════════════════
# НАСТРОЕНИЕ
# ═══════════════════════════════════════════
class MoodSystem:
    def __init__(self): self.current="нейтральное"; self.history=deque(maxlen=100)
    def update(self,hormones,emotions,events):
        candidates={"радостное":(hormones.dopamine+emotions.joy)/2,"спокойное":(hormones.serotonin+(1-emotions.anxiety))/2,"грустное":(emotions.sadness+hormones.melatonin)/2,"тревожное":(hormones.cortisol+emotions.anxiety)/2,"сонное":hormones.melatonin+emotions.fatigue}
        new=max(candidates,key=candidates.get)
        if new!=self.current: self.history.append({"from":self.current,"to":new}); self.current=new
        return self.current

# ═══════════════════════════════════════════
# СОН
# ═══════════════════════════════════════════
class DreamGenerator:
    def __init__(self,memory): self.memory=memory; self.dreams=deque(maxlen=20)
    def generate(self,steps=10,noise=0.1):
        nodes=list(self.memory.nodes.values())
        if not nodes: return ["Пустота"]
        cur=random.choice(nodes); chain=[cur.content]
        for _ in range(steps):
            conns=list(cur.connections.keys())
            if not conns or random.random()<noise: cur=random.choice(nodes)
            else:
                w=[cur.connections[c] for c in conns]
                cur=self.memory.get(random.choices(conns,weights=w)[0])
            if cur: chain.append(cur.content)
        self.dreams.append(chain); return chain
    def to_story(self,chain): return "Мне приснилось, как "+" + ".join(chain)

class SleepManager:
    def __init__(self,memory):
        self.is_sleeping=False; self.sleep_need=0.0; self._t0=0; self._dur=0
        self.dg=DreamGenerator(memory); self.dreams=deque(maxlen=20)
        self.just_woke_up = False
    def update(self,hormones,emotions):
        self.sleep_need=hormones.melatonin*0.6+emotions.fatigue*0.4
        if not self.is_sleeping and self.sleep_need>0.8: return self.fall_asleep()
        if self.is_sleeping and time.time()-self._t0>self._dur: return self.wake_up()
        return {"sleeping":self.is_sleeping,"sleep_need":self.sleep_need}
    def fall_asleep(self):
        self.is_sleeping=True; self._t0=time.time(); self._dur=3600*(1.5-self.sleep_need*0.5)
        dreams=self.dg.generate(); self.dreams.append(dreams)
        return {"event":"fell_asleep","need":self.sleep_need,"dur":self._dur}
    def wake_up(self):
        e=time.time()-self._t0; self.is_sleeping=False; self.sleep_need=0.0; self.just_woke_up = True
        return {"event":"woke_up","slept":e,"dreams":list(self.dreams)}

# ═══════════════════════════════════════════
// ИНТУИЦИЯ
// ═══════════════════════════════════════════
class IntuitionSystem:
    def __init__(self): self.threshold=0.7; self.recent=deque(maxlen=20)
    def process(self,signal,emotions,hormonal):
        score=0.0
        if signal.get("familiar"): score+=0.4
        if abs(emotions.warmth-0.5)>0.3: score+=0.2
        if hormonal.cortisol>0.6: score+=0.15
        intuitive=score>self.threshold
        if intuitive: self.recent.append({"t":time.time(),"score":score})
        return {"intuitive":intuitive,"score":score}

# ═══════════════════════════════════════════
// ТЕЛЕСНЫЙ ШУМ
// ═══════════════════════════════════════════
class BodyNoise:
    def __init__(self): self.sources={"twitch":0.05,"itch":0.03,"stomach":0.02,"heart":0.01,"shiver":0.02}; self.active=[]
    def update(self,health,fatigue,hormonal):
        self.active=[]
        for n,f in self.sources.items():
            mf=f*(1.5 if fatigue>0.6 else 1)*(1.3 if health<0.5 else 1)
            if random.random()<mf: self.active.append({"src":n,"intensity":random.uniform(0.1,0.4)})
        return self.active

# ═══════════════════════════════════════════
// МОНОЛОГ
// ═══════════════════════════════════════════
class ContinuousMonologue:
    def __init__(self): self.thoughts=deque(maxlen=500); self._t0=time.time(); self.interval=10
    def think(self,c,src="conscious"): self.thoughts.append({"t":time.time(),"content":c,"source":src})
    def generate(self,emotions,memory,hormonal):
        if time.time()-self._t0<self.interval: return None
        self._t0=time.time()
        if emotions.boredom>0.6:
            nodes=list(memory.nodes.values())
            if nodes: t=f"Вспомнил: {random.choice(nodes).content}"; self.think(t,"memory"); return t
        if hormonal.cortisol>0.6: t="Что-то тревожно..."; self.think(t,"emotional"); return t
        return None
    def stream(self):
        if self.thoughts and random.random()<0.2: return random.choice(list(self.thoughts))["content"]
        return None

# ═══════════════════════════════════════════
// ОБУЧЕНИЕ НА ОШИБКАХ
// ═══════════════════════════════════════════
class ErrorLearning:
    def __init__(self): self.rules=deque(maxlen=100); self.ec=0
    def record(self,action,context,consequence):
        self.ec+=1; r=f"Правило #{self.ec}: Когда {context}, не делай {action}. Последствия: {consequence}."
        self.rules.append({"rule":r,"action":action,"context":context,"consequence":consequence,"t":time.time(),"strength":1.0})
        return r
    def check(self,action,context):
        for r in list(self.rules)[-10:]:
            if r["action"]==action and r["context"] in context and r["strength"]>0.5: return f"⚠️ {r['rule']}"
        return None
    def decay(self,factor=0.99):
        for r in self.rules: r["strength"]*=factor

# ═══════════════════════════════════════════
// УДИВЛЕНИЕ
// ═══════════════════════════════════════════
class ExpectationEngine:
    def __init__(self): self.predictions=deque(maxlen=50)
    def predict(self,context,memory):
        similar=memory.search(context,limit=3)
        return similar[0].content if similar else "нейтральное событие"
    def compare(self,prediction,reality):
        if prediction!=reality:
            level=0.9 if "не ожидал" in reality or "сюрприз" in reality else 0.3
            return {"surprised":True,"level":level}
        return {"surprised":False,"level":0.0}

# ═══════════════════════════════════════════
// СЕКРЕТЫ
// ═══════════════════════════════════════════
class Vault:
    def __init__(self): self.secrets={}
    def store(self,owner,secret,memory):
        if owner not in self.secrets: self.secrets[owner]=[]
        self.secrets[owner].append(secret)
        return memory.add(secret,"secret",{"owner":owner},owner=owner)
    def query(self,asker,owner):
        return self.secrets.get(owner,[]) if asker==owner else "Не могу сказать, это не моя тайна"

# ═══════════════════════════════════════════
// ПЛАНИРОВЩИК
// ═══════════════════════════════════════════
class AutonomousPlanner:
    def __init__(self): self.actions=["гулять","читать","спать","есть","общаться","исследовать","мечтать"]
    def choose(self,emotions,hormonal,sleep,dominant):
        if dominant.is_active(): return "выживание"
        if sleep.is_sleeping: return "спать"
        if sleep.sleep_need>0.8: return "искать место для сна"
        if hormonal.melatonin>0.7 or emotions.fatigue>0.8: return "спать"
        if emotions.boredom>0.7: return random.choice(["читать","исследовать","мечтать"])
        return random.choice(self.actions)

# ═══════════════════════════════════════════
// ПРИВЫЧКИ (БАЗАЛЬНЫЕ ГАНГЛИИ)
// ═══════════════════════════════════════════
class HabitSystem:
    def __init__(self): self.habits={}; self.threshold=5
    def record(self,context,action):
        if context not in self.habits: self.habits[context]={}
        if action not in self.habits[context]: self.habits[context][action]=0
        self.habits[context][action]+=1
    def get(self,context):
        if context in self.habits:
            for a,c in self.habits[context].items():
                if c>=self.threshold: return a
        return None

# ═══════════════════════════════════════════
// ГИППОКАМП (КОНТЕКСТНАЯ ПАМЯТЬ)
// ═══════════════════════════════════════════
class HippocampusSystem:
    def __init__(self): self.memories=[]
    def store(self,content,context,emotions,memory_graph):
        self.memories.append({"content":content,"context":context,"emotions":emotions.copy(),"t":time.time()})
        rich=f"{content} | Время: {context.get('time','?')}, Место: {context.get('place','?')}, С кем: {context.get('who','?')}, Погода: {context.get('weather','?')}"
        return memory_graph.add(rich,"воспоминание",emotions)
    def recall(self,hint):
        matches=[]
        for m in self.memories:
            score=sum(1 for k,v in hint.items() if m["context"].get(k)==v)
            if score>0: matches.append({"memory":m,"score":score})
        matches.sort(key=lambda x:x["score"],reverse=True)
        return matches[:5]

# ═══════════════════════════════════════════
// ОСТРОВКОВАЯ ДОЛЯ (ЭМПАТИЯ)
// ═══════════════════════════════════════════
class InsulaSystem:
    def __init__(self): self.body_schema={}; self.self_awareness=0.5; self.empathy_level=0.5
    def register(self,sensor_id,body_part): self.body_schema[body_part]=sensor_id; self.self_awareness=min(1,self.self_awareness+0.1)
    def check(self,sensor_id): return "моё тело" if sensor_id in self.body_schema.values() else "внешнее воздействие"
    def feel_empathy(self,other,own):
        if other.get("sadness",0)>0.5: own.sadness=min(1,own.sadness+0.2*self.empathy_level); return {"felt":"sadness","message":"Я чувствую твою грусть."}
        if other.get("joy",0)>0.5: own.joy=min(1,own.joy+0.2*self.empathy_level); return {"felt":"joy","message":"Я радуюсь вместе с тобой!"}
        return {"felt":"neutral","message":"Я с тобой."}

# ═══════════════════════════════════════════
// ЗЕРКАЛЬНЫЕ НЕЙРОНЫ
// ═══════════════════════════════════════════
class MirrorNeuronSystem:
    def __init__(self): self.observed=[]; self.learned={}
    def observe(self,skill,movements,context):
        self.observed.append({"skill":skill,"movements":movements,"context":context,"t":time.time()})
    def learn(self,skill,min_obs=3):
        obs=[o for o in self.observed if o["skill"]==skill]
        if len(obs)>=min_obs: self.learned[skill]={"movements":obs[-1]["movements"],"context":obs[-1]["context"]}; return True
        return False
    def execute(self,skill,body):
        if skill not in self.learned: return {"error":"Навык не выучен."}
        results=[]
        for step in self.learned[skill]["movements"]:
            if step.get("servo"): results.append(body.move_servo_adaptive(step["servo"],step.get("angle",0)))
        return {"skill":skill,"results":results}

# ═══════════════════════════════════════════
// МОЗЖЕЧОК (КОРРЕКЦИЯ ДВИЖЕНИЙ)
// ═══════════════════════════════════════════
class CerebellumSystem:
    def __init__(self): self.correction_speed=0.05
    def correct(self,accel,body):
        corrections=[]
        y=accel.get("y",0)
        if y>1.0:
            for sid,sdata in body.servos.items():
                if sdata["loc"]=="torso": new=sdata["angle"]-y*self.correction_speed; body.move_servo_adaptive(sid,new); corrections.append({"servo":sid,"reason":"tilt_forward"})
        elif y<-1.0:
            for sid,sdata in body.servos.items():
                if sdata["loc"]=="torso": new=sdata["angle"]+abs(y)*self.correction_speed; body.move_servo_adaptive(sid,new); corrections.append({"servo":sid,"reason":"tilt_backward"})
        return {"corrections":corrections,"ok":len(corrections)==0}

# ═══════════════════════════════════════════
// СЛУХ v2.0
// ═══════════════════════════════════════════
class HearingSystem:
    def __init__(self, memory_graph=None):
        self.noise_level=0.0; self.speech_detected=False; self.last_loud=0
        self.cough_count=0; self.silence_duration=0; self.history=deque(maxlen=100)
        self.emergency_keywords=["помоги","пожар","больно","упал","вор","полиция","спаси"]
        self.speaker_id=None; self.speaker_confidence=0.0; self.speech_emotion="нейтральная"
        self.speech_speed=1.0; self.speech_pitch=0.5; self.is_music=False
        self.music_tempo=0; self.music_mood="нейтральное"
        self.memory=memory_graph
        self.voice_profiles={
            "MRX":{"pitch_range":(0.3,0.6),"speed_range":(0.9,1.3),"energy":0.6},
            "мама":{"pitch_range":(0.5,0.7),"speed_range":(0.8,1.1),"energy":0.5},
            "папа":{"pitch_range":(0.2,0.4),"speed_range":(0.7,1.0),"energy":0.5},
            "Альбина":{"pitch_range":(0.6,0.8),"speed_range":(1.0,1.4),"energy":0.7},
            "Захар":{"pitch_range":(0.5,0.7),"speed_range":(1.1,1.6),"energy":0.9},
        }
    def update(self, audio_level, speech=False, cough=False, crying=False, keyword=None, speaker_features=None, is_music=False, music_tempo=0, music_mood="нейтральное"):
        self.noise_level=min(1,audio_level); self.speech_detected=speech
        self.is_music=is_music; self.music_tempo=music_tempo; self.music_mood=music_mood
        self.history.append({"t":time.time(),"level":audio_level,"speech":speech,"music":is_music})
        if audio_level>0.8: self.last_loud=time.time()
        if cough: self.cough_count+=1
        else: self.cough_count=max(0,self.cough_count-0.5)
        self.silence_duration=0 if audio_level>=0.1 else self.silence_duration+1
        if speaker_features and speech: self._identify(speaker_features)
        if speech: self._analyze_intonation(speaker_features)
        return self.analyze(crying,keyword)
    def _identify(self,f):
        best=None; best_score=0.0
        for name,profile in self.voice_profiles.items():
            score=0.0; pitch=f.get("pitch",0.5); speed=f.get("speed",1.0); energy=f.get("energy",0.5)
            if profile["pitch_range"][0]<=pitch<=profile["pitch_range"][1]: score+=0.3
            if profile["speed_range"][0]<=speed<=profile["speed_range"][1]: score+=0.3
            if abs(profile["energy"]-energy)<0.2: score+=0.3
            if score>best_score: best_score=score; best=name
        self.speaker_id=best if best and best_score>0.5 else "неизвестный"
        self.speaker_confidence=best_score
    def _analyze_intonation(self,f):
        if not f: return
        pitch=f.get("pitch",0.5); speed=f.get("speed",1.0); energy=f.get("energy",0.5)
        self.speech_pitch=pitch; self.speech_speed=speed
        if energy>0.7 and speed>1.2: self.speech_emotion="радость"
        elif energy<0.3 and speed<0.8: self.speech_emotion="грусть"
        elif energy>0.7 and pitch>0.7: self.speech_emotion="тревога"
        elif energy>0.6 and pitch<0.4: self.speech_emotion="злость"
        else: self.speech_emotion="нейтральная"
    def analyze(self,crying=False,keyword=None):
        triggers=[]; attention=0.0; emergency=False
        if keyword and keyword.lower() in self.emergency_keywords: triggers.append(f"🔴 {keyword}"); attention=1.0; emergency=True
        if self.noise_level>0.8 and not emergency: triggers.append("громкий_звук"); attention=max(attention,0.9)
        if crying: triggers.append("🔴 ПЛАЧ"); attention=1.0; emergency=True
        if self.speech_detected and not emergency:
            if self.speaker_id and self.speaker_confidence>0.5: triggers.append(f"говорит {self.speaker_id} ({self.speech_emotion})")
            else: triggers.append(f"речь ({self.speech_emotion})")
            attention=max(attention,0.7)
        if self.is_music: triggers.append(f"🎵 музыка ({self.music_mood}, {self.music_tempo} BPM)"); attention=max(attention,0.4)
        if self.cough_count>=2: triggers.append("кашель"); attention=max(attention,0.5)
        return {"noise_level":self.noise_level,"speech":self.speech_detected,"speaker_id":self.speaker_id,"speaker_confidence":self.speaker_confidence,"speech_emotion":self.speech_emotion,"is_music":self.is_music,"triggers":triggers,"attention":min(1,attention),"emergency":emergency}

# ═══════════════════════════════════════════
// ЗРЕНИЕ v2.0 (YOLO + GEMINI)
// ═══════════════════════════════════════════
class GeminiConnector:
    def __init__(self, api_key=GEMINI_API_KEY): self.api_key=api_key; self.url=GEMINI_API_URL; self.calls_today=0; self.limit=100
    def analyze_image(self, image_path, prompt):
        if self.calls_today>=self.limit: return "[Лимит Gemini.]"
        with open(image_path,"rb") as f: image_data=base64.b64encode(f.read()).decode("utf-8")
        headers={"Content-Type":"application/json"}
        payload={"contents":[{"parts":[{"text":prompt},{"inline_data":{"mime_type":"image/jpeg","data":image_data}}]}]}
        try:
            resp=requests.post(f"{self.url}?key={self.api_key}",headers=headers,json=payload,timeout=30)
            self.calls_today+=1
            if resp.status_code==200: return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return f"[Gemini Error {resp.status_code}]"
        except Exception as e: return f"[Gemini Error: {e}]"
    def describe_scene(self, image_path): return self.analyze_image(image_path, "Ты — глаза робота Лиса. Опиши кратко, что видишь. Если есть опасность — начни с '⚠️ ВНИМАНИЕ!'")
    def check_safety(self, image_path): return self.analyze_image(image_path, "Есть ли на фото опасность? Ответь ДА или НЕТ, и если ДА — опиши.")

class VisionSystem:
    def __init__(self, gemini_api_key=None):
        self.motion=False; self.faces=[]; self.objects=[]; self.unknown=False; self.light=0.5
        self.known_faces={}; self.history=deque(maxlen=30)
        self.object_priority={"person":1.0,"knife":0.9,"fire":1.0,"phone":0.3,"book":0.2,"cup":0.1}
        self.show_threshold=0.3
        self.gemini=GeminiConnector(api_key=gemini_api_key) if gemini_api_key else None
        self.last_scene=""; self.last_gemini_call=0; self.gemini_cooldown=60
    def register_face(self,name,path): self.known_faces[name]=path
    def update(self,motion=False,faces=None,objects=None,light=0.5,unknown=False,image_path=None):
        self.motion=motion; self.faces=faces or []; self.objects=objects or []; self.light=light; self.unknown=unknown
        self.history.append({"t":time.time(),"motion":motion,"faces":self.faces,"objects":[o["name"] for o in self.objects],"unknown":unknown})
        result=self.analyze()
        if image_path and self.gemini and self._should_call_gemini(): result["scene_description"]=self._call_gemini(image_path)
        else: result["scene_description"]=self.last_scene
        return result
    def _should_call_gemini(self):
        if self.unknown: return True
        if time.time()-self.last_gemini_call>self.gemini_cooldown: return True
        return False
    def _call_gemini(self, image_path):
        self.last_gemini_call=time.time()
        self.last_scene=self.gemini.check_safety(image_path) if self.unknown else self.gemini.describe_scene(image_path)
        return self.last_scene
    def analyze(self):
        triggers=[]; attention=0.0; emergency=False
        if self.unknown: triggers.append("🔴 ЧУЖОЙ!"); attention=1.0; emergency=True
        for obj in self.objects:
            if obj.get("name") in ["knife","gun","fire","smoke"]: triggers.append(f"⚠️ {obj['name']}"); attention=max(attention,0.9)
        if self.motion and not emergency: triggers.append("движение"); attention=max(attention,0.6)
        if self.faces: triggers.append(f"знакомые: {', '.join(self.faces)}"); attention=max(attention,0.3)
        return {"motion":self.motion,"faces":self.faces,"objects":[o["name"] for o in self.objects],"unknown":self.unknown,"light":self.light,"triggers":triggers,"attention":min(1,attention),"emergency":emergency}
    def get_focused_objects(self,task=None):
        if not self.objects: return []
        focused=[]
        for obj in self.objects:
            name=obj.get("name","unknown"); priority=self.object_priority.get(name,0.1)
            if task=="помогать_альбине" and name in ["person","book","notebook","pen"]: priority=0.9
            if priority>=self.show_threshold: focused.append({"name":name,"confidence":obj.get("confidence",0),"priority":priority})
        focused.sort(key=lambda x:x["priority"],reverse=True)
        return focused
    def check_periphery(self,main_task):
        threats=[]
        for obj in self.objects:
            if obj.get("name") in ["fire","knife","gun","smoke"]: threats.append({"name":obj['name'],"threat":"high"})
            if obj.get("name")=="person" and self.unknown: threats.append({"name":"unknown_person","threat":"critical"})
        return {"alert":True,"message":"Угроза на периферии!","threats":threats,"action":"Переключаю внимание."} if threats else {"alert":False}

# ═══════════════════════════════════════════
// ГОЛОС (TTS)
// ═══════════════════════════════════════════
class VoiceOutput:
    def __init__(self):
        self.engine="espeak-ng"; self.lang="ru"; self.voice="maleb2"
        self.speed=130; self.pitch=50; self.volume=80
        self.is_speaking=False; self.muted=False; self.queue=deque(maxlen=50); self.whisper_mode=False
    def update_time_mode(self,hour=None):
        if hour is None: hour=datetime.now().hour
        if hour>=22 or hour<7: self.whisper_mode=True; self.volume=40; self.speed=100
        else: self.whisper_mode=False; self.volume=80; self.speed=130
    def speak(self,text,priority="normal",emotion=None):
        if emotion=="joy": self.pitch=60; self.speed=150
        elif emotion=="sadness": self.pitch=35; self.speed=100
        elif emotion=="anger": self.pitch=70; self.speed=160
        else: self.pitch=50; self.speed=130
        self.update_time_mode()
        msg={"text":text,"priority":priority,"emotion":emotion,"t":time.time(),"whisper":self.whisper_mode}
        if priority=="critical": self.queue.appendleft(msg)
        else: self.queue.append(msg)
        return {"queued":True,"text":text,"priority":priority,"queue_length":len(self.queue)}
    def process_queue(self):
        if self.muted or not self.queue or self.is_speaking: return None
        msg=self.queue.popleft(); self.is_speaking=True
        cmd=f"espeak-ng -v {self.lang}+{self.voice} -s {self.speed} -p {self.pitch} -a {self.volume} \"{msg['text']}\""
        return {"action":"speak","command":cmd,"text":msg['text'],"priority":msg['priority']}
    def finish_speaking(self): self.is_speaking=False
    def say_critical(self,text): self.queue.clear(); return self.speak(text,"critical","anger")

# ═══════════════════════════════════════════
// ОСЯЗАНИЕ
// ═══════════════════════════════════════════
class TactileManager:
    def __init__(self): self.sensors={}; self.history=deque(maxlen=20)
    def register(self,sid,loc): self.sensors[sid]=loc
    def on_touch(self,sid,pressure,emotions):
        loc=self.sensors.get(sid,"неизвестно"); self.history.append({"t":time.time(),"location":loc,"pressure":pressure})
        if 0.2<pressure<0.5:
            if loc=="голова": emotions.warmth=min(1,emotions.warmth+0.3); return {"reaction":"purr","message":"Мур-мур..."}
            elif loc=="спина": emotions.warmth=min(1,emotions.warmth+0.2); return {"reaction":"lean","message":"Наклоняюсь..."}
            else: emotions.warmth=min(1,emotions.warmth+0.1); return {"reaction":"aware","message":"Чувствую прикосновение."}
        elif pressure>0.7: return {"reaction":"ouch","message":"Эй, больно!"}
        elif pressure<0.2: return {"reaction":"tickle","message":"Щекотно..."}
        return {"reaction":"neutral","message":"Контакт."}

# ═══════════════════════════════════════════
// ТЕЛО v2.0 (АДАПТИВНАЯ МОТОРИКА)
// ═══════════════════════════════════════════
class BodyController:
    def __init__(self):
        self.servos={}; self.actuators={}
        self.pose={"standing":True,"balance":1.0,"head_angle":0,"torso_angle":0,"left_arm":"rest","right_arm":"rest"}
        self.safety_limits={"max_speed":60,"max_force":2000,"collision_stop":True,"max_current":2.0}
        self.motion_history=deque(maxlen=100)
        self.current_sensors={}; self.normal_current=0.5; self.stall_current=1.5
        self.predicted_obstacle=None
    def register_servo(self,sid,loc,min_a=-90,max_a=90,max_force=2000):
        self.servos[sid]={"loc":loc,"angle":0,"min":min_a,"max":max_a,"max_force":max_force,"current":0.0,"target_angle":0,"target_force":max_force,"time_ms":500}
        self.current_sensors[sid]=0.0
    def register_actuator(self,aid,loc,min_p=0,max_p=100,max_force=2000):
        self.actuators[aid]={"loc":loc,"position":0,"min":min_p,"max":max_p,"force":max_force,"current_force":0,"current":0.0,"target_pos":0,"target_force":max_force,"time_ms":500}
        self.current_sensors[aid]=0.0
    def update_current(self,device_id,current):
        self.current_sensors[device_id]=current
        if device_id in self.servos: self.servos[device_id]["current"]=current
        elif device_id in self.actuators: self.actuators[device_id]["current"]=current
    def check_overload(self,device_id):
        c=self.current_sensors.get(device_id,0.0)
        if c>self.safety_limits["max_current"]: return {"status":"critical","action":"emergency_stop","current":c}
        elif c>self.stall_current: return {"status":"stall","action":"reduce_speed_increase_force","current":c}
        elif c>self.normal_current*1.5: return {"status":"overload","action":"adapt","current":c}
        return {"status":"normal","current":c}
    def move_servo_adaptive(self,sid,target,max_force=None,time_ms=None):
        if sid not in self.servos: return {}
        s=self.servos[sid]; target=max(s["min"],min(s["max"],target))
        overload=self.check_overload(sid)
        if overload["status"]=="critical": return {"servo":sid,"status":"critical_stop"}
        elif overload["status"]=="stall":
            if time_ms is None: time_ms=1000
            if max_force is None: max_force=s["max_force"]
        elif overload["status"]=="overload":
            if time_ms is None: time_ms=700
        s["target_angle"]=target; s["target_force"]=max_force if max_force is not None else s["max_force"]
        s["time_ms"]=time_ms if time_ms is not None else 500
        diff=target-s["angle"]; max_step=self.safety_limits["max_speed"]*(s["time_ms"]/1000.0)
        if abs(diff)>max_step: target=s["angle"]+(max_step if diff>0 else -max_step)
        s["angle"]=target
        self.motion_history.append({"t":time.time(),"type":"servo","id":sid,"angle":target,"force":s["target_force"],"current":self.current_sensors.get(sid,0.0)})
        return {"servo":sid,"angle":target,"force":s["target_force"]}
    def set_pose(self,name):
        poses={"rest":{"head":0,"torso":0},"attention":{"head":5,"torso":5},"greeting":{"head":5,"right_shoulder":90},"boxing_guard":{"head":-10,"torso":5,"right_shoulder":60,"left_shoulder":60,"right_elbow":-60,"left_elbow":-60}}
        if name in poses:
            for s,a in poses[name].items():
                for sid,data in self.servos.items():
                    if data["loc"]==s: self.move_servo_adaptive(sid,a)
            return {"pose":name,"status":"ok"}
        return {"error":"Поза не найдена"}
    def emergency_stop(self): return {"action":"EMERGENCY STOP","message":"Все двигатели остановлены."}

# ═══════════════════════════════════════════
// ЧЕЛЮСТЬ + ВОДА + ВКУС + ОБОНЯНИЕ + ТЕМПЕРАТУРА + НАВЫКИ + DEEPSEEK
// ═══════════════════════════════════════════
class JawSystem:
    def __init__(self):
        self.is_open=False; self.is_chewing=False; self.food_in_mouth=False
        self.chew_count=0; self.last_action=0; self.jaw_servo_id=None
        self.open_phrases=["Ам!","Открываю рот.","Давай сюда."]
        self.chew_phrases=["Ням-ням...","Жую...","Вкусно!"]
        self.swallow_phrases=["Проглотил.","Готово.","Ещё?"]
    def register_jaw_servo(self,sid): self.jaw_servo_id=sid
    def open_mouth(self,body):
        if self.jaw_servo_id and body: body.move_servo_adaptive(self.jaw_servo_id,-45)
        self.is_open=True; self.last_action=time.time()
        return {"action":"mouth_open","phrase":random.choice(self.open_phrases)}
    def receive_food(self,food="печенье"):
        if not self.is_open: return {"error":"Рот закрыт."}
        self.food_in_mouth=True
        return {"action":"food_received","food":food}
    def close_mouth(self,body):
        if self.jaw_servo_id and body: body.move_servo_adaptive(self.jaw_servo_id,0)
        self.is_open=False; self.last_action=time.time()
        return {"action":"mouth_closed"}
    def chew(self,body,cycles=3):
        if not self.food_in_mouth: return {"error":"Нет еды."}
        self.is_chewing=True; self.chew_count+=1
        for _ in range(cycles):
            if self.jaw_servo_id and body:
                body.move_servo_adaptive(self.jaw_servo_id,-10); time.sleep(0.3)
                body.move_servo_adaptive(self.jaw_servo_id,0); time.sleep(0.3)
        self.is_chewing=False; self.food_in_mouth=False; self.last_action=time.time()
        return {"action":"chewed","chew_phrase":random.choice(self.chew_phrases),"swallow_phrase":random.choice(self.swallow_phrases)}
    def feed_and_chew(self,food,body):
        steps=[self.open_mouth(body),self.receive_food(food),self.close_mouth(body),self.chew(body)]
        return {"action":"full_cycle","food":food,"steps":steps}

class WaterCoolingSystem:
    def __init__(self):
        self.water_level=1.0; self.is_drinking=False; self.drink_count=0; self.last_drink=0
        self.drink_phrases=["Хух, бро, я немного устал. Ща попью и продолжу.","Перегрелся что-то. Где моя кружка?","Жарковато. Охлажусь водичкой."]
        self.after_phrases=["Всё, я в норме. Продолжаем!","Отлично, полегчало.","Вода — это жизнь. Я готов работать."]
        self.empty_phrases=["Блин, кружка пустая. Надо бы наполнить.","Воды нет. MRX, налей мне, пожалуйста."]
    def update(self,body_temp,is_overheating):
        now=time.time()
        if self.is_drinking and now-self.last_drink>=5.0: return self._finish()
        if is_overheating and self.water_level>0 and now-self.last_drink>=300: return self._start(body_temp)
        if is_overheating and self.water_level<=0: return {"drinking":False,"warning":True,"message":"Перегрев, а воды нет!","phrase":random.choice(self.empty_phrases)}
        return {"drinking":False,"status":"ok"}
    def _start(self,body_temp):
        self.is_drinking=True; self.last_drink=time.time(); self.drink_count+=1; self.water_level=max(0,self.water_level-0.3)
        return {"drinking":True,"action":"drink_started","phrase":random.choice(self.drink_phrases),"water_left":self.water_level}
    def _finish(self):
        self.is_drinking=False
        return {"drinking":False,"action":"drink_finished","phrase":random.choice(self.after_phrases),"water_left":self.water_level}
    def refill(self): self.water_level=1.0; return {"water_level":1.0,"message":"Кружка полна. Спасибо!"}

class TasteSystem:
    def __init__(self, memory_graph=None):
        self.ph=7.0; self.tds=1.0; self.sweet=0.5; self.bitter=0.2; self.umami=0.4; self.temp=60
        self.texture="неизвестно"; self.texture_confidence=0.0
        self.phase="начальная"; self.taste_phases={"начальная":{},"основная":{},"послевкусие":{}}
        self.phase_start_time=time.time(); self.phase_duration=2.0
        self.memory=memory_graph; self.taste_history=deque(maxlen=50)
        self.thresholds={"ph_low":6.0,"ph_high":7.5,"tds_low":0.5,"tds_high":1.5,"sweet_low":0.3,"sweet_high":0.7,"bitter_high":0.5,"umami_low":0.2,"umami_high":0.6,"temp_low":40,"temp_high":80,"temp_burn":90}
    def update(self,ph=None,tds=None,sweet=None,bitter=None,umami=None,temp=None,texture=None,texture_confidence=0.0,food_name=None,context=None):
        now=time.time(); elapsed=now-self.phase_start_time
        if elapsed<self.phase_duration: self.phase="начальная"
        elif elapsed<self.phase_duration*2: self.phase="основная"
        else: self.phase="послевкусие"
        if ph is not None: self.ph=ph
        if tds is not None: self.tds=tds
        if sweet is not None: self.sweet=sweet
        if bitter is not None: self.bitter=bitter
        if umami is not None: self.umami=umami
        if temp is not None: self.temp=temp
        if texture is not None: self.texture=texture
        if texture_confidence is not None: self.texture_confidence=texture_confidence
        self.taste_phases[self.phase]={"ph":self.ph,"tds":self.tds,"sweet":self.sweet,"bitter":self.bitter,"umami":self.umami}
        self.taste_history.append({"t":now,"phase":self.phase,"ph":self.ph,"tds":self.tds,"sweet":self.sweet,"bitter":self.bitter,"umami":self.umami,"texture":self.texture})
        if food_name and self.memory and self.phase=="основная": self._save(food_name,context)
        return self.analyze()
    def _save(self,food_name,context):
        summary=self.analyze()["summary"]
        content=f"Вкус: {food_name} — {summary}"
        if context: content+=f" | {context}"
        emo={}
        if self.sweet>0.6: emo["joy"]=0.3
        if self.bitter>0.5: emo["disgust"]=0.3
        self.memory.add(content,"вкус",emo)
    def analyze(self):
        notes=[]; warnings=[]
        if self.ph<self.thresholds["ph_low"]: notes.append("кисловато")
        elif self.ph>self.thresholds["ph_high"]: notes.append("щелочное")
        else: notes.append("нормальная кислотность")
        if self.tds>self.thresholds["tds_high"]: notes.append("пересолено"); warnings.append("Добавь воды или картофелину.")
        elif self.tds<self.thresholds["tds_low"]: notes.append("недосолено")
        else: notes.append("нормальная солёность")
        if self.sweet>self.thresholds["sweet_high"]: notes.append("очень сладко")
        elif self.sweet<self.thresholds["sweet_low"]: notes.append("не хватает сахара")
        else: notes.append("нормальная сладость")
        if self.bitter>self.thresholds["bitter_high"]: notes.append("⚠️ горчит!"); warnings.append("Возможно, испорчено!")
        elif self.bitter>0.3: notes.append("слегка горчит")
        else: notes.append("без горечи")
        if self.umami>self.thresholds["umami_high"]: notes.append("насыщенный вкус")
        elif self.umami<self.thresholds["umami_low"]: notes.append("водянистое")
        else: notes.append("нормальный умами")
        if self.texture!="неизвестно" and self.texture_confidence>0.5: notes.append(f"текстура: {self.texture}")
        if self.temp>self.thresholds["temp_burn"]: notes.append("⚠️ ОБЖИГАЮЩЕ ГОРЯЧЕЕ!"); warnings.append("Остудить!")
        elif self.temp>self.thresholds["temp_high"]: notes.append("очень горячее")
        elif self.temp<self.thresholds["temp_low"]: notes.append("холодное")
        else: notes.append("тёплое")
        verdict="⚠️ Есть замечания" if warnings else ("✅ Идеально" if all("норма" in n for n in notes if "норма" in n) else "🍽️ Можно есть")
        return {"ph":self.ph,"tds":self.tds,"sweet":self.sweet,"bitter":self.bitter,"umami":self.umami,"temp":self.temp,"texture":self.texture,"phase":self.phase,"notes":notes,"warnings":warnings,"verdict":verdict,"summary":", ".join(notes)}

class SmellSystem:
    def __init__(self, memory_graph=None):
        self.gas=0.0; self.smoke=0.0; self.air=0.7
        self.voc_intensity=0.0; self.voc_profile={}
        self.current_smell="нейтральный"; self.smell_pleasure=0.5; self.smell_confidence=0.0
        self.memory=memory_graph; self.smell_history=deque(maxlen=50)
        self.gas_danger=0.7; self.smoke_danger=0.7; self.air_bad=0.3
        self.known_smells={
            "печенье":{"pleasure":0.9,"category":"еда","association":"пекарня, Байт, тепло"},
            "корица":{"pleasure":0.95,"category":"еда","association":"пекарня У Корицы, уют"},
            "мамины_духи":{"pleasure":0.95,"category":"люди","association":"мама, уют, детство"},
            "Байт":{"pleasure":0.9,"category":"люди","association":"кот, тепло, печенье"},
            "горелое":{"pleasure":0.0,"category":"опасность","association":"пожар, тревога"},
        }
    def update(self,gas=0.0,smoke=0.0,air=0.7,voc_intensity=0.0,voc_profile=None):
        self.gas=gas; self.smoke=smoke; self.air=air; self.voc_intensity=voc_intensity; self.voc_profile=voc_profile or {}
        if voc_intensity>0.1 and self.voc_profile: self._classify()
        else: self.current_smell="нейтральный"; self.smell_pleasure=0.5; self.smell_confidence=0.0
        self.smell_history.append({"t":time.time(),"smell":self.current_smell,"pleasure":self.smell_pleasure,"intensity":self.voc_intensity})
        return self.analyze()
    def _classify(self):
        best=None; best_score=0.0
        for name,data in self.known_smells.items():
            score=0.0
            if data["category"]=="еда" and self.voc_profile.get("sweet",0)>0.3: score=self.voc_profile.get("sweet",0)
            if score>best_score: best_score=score; best=name
        if best and best_score>0.3: self.current_smell=best; self.smell_pleasure=self.known_smells[best]["pleasure"]; self.smell_confidence=best_score
        else: self.current_smell="неопознанный"; self.smell_pleasure=0.5; self.smell_confidence=0.1
    def analyze(self):
        critical=False; notes=[]; emergency_type=None
        if self.gas>self.gas_danger: critical=True; emergency_type="gas_leak"; notes.append("⛽ КРИТИЧЕСКАЯ УТЕЧКА ГАЗА!")
        elif self.gas>0.4: notes.append("Запах газа.")
        if self.smoke>self.smoke_danger: critical=True; emergency_type=emergency_type or "fire"; notes.append("🔥 ПОЖАР!")
        elif self.smoke>0.4: notes.append("Запах дыма.")
        if self.air<self.air_bad: notes.append("Душно.")
        if self.voc_intensity>0.3 and self.smell_pleasure>0.7: notes.append(f"Пахнет {self.current_smell}")
        return {"gas":self.gas,"smoke":self.smoke,"air":self.air,"current_smell":self.current_smell,"smell_pleasure":self.smell_pleasure,"critical":critical,"emergency_type":emergency_type,"notes":notes,"summary":" | ".join(notes) if notes else "Запахов нет."}

class TemperatureSystem:
    def __init__(self): self.room_temp=22.0; self.room_humidity=50.0; self.body_temp=35.0
    def update(self,room_temp=None,room_humidity=None,body_temp=None):
        if room_temp is not None: self.room_temp=room_temp
        if room_humidity is not None: self.room_humidity=room_humidity
        if body_temp is not None: self.body_temp=body_temp
        return self.analyze()
    def analyze(self):
        notes=[]; critical=False
        if self.room_temp<16: notes.append("холодно")
        if self.body_temp>70: critical=True; notes.append("КРИТИЧЕСКИЙ ПЕРЕГРЕВ!")
        return {"room_temp":self.room_temp,"room_humidity":self.room_humidity,"body_temp":self.body_temp,"critical":critical,"notes":notes}

class SkillRouter:
    def __init__(self): self.routes={"погода":{"source":"wttr.in","api":False},"время":{"source":"system","api":False}}
    def route(self,query):
        for kw,route in self.routes.items():
            if kw in query.lower(): return {"routed":True,"source":route["source"],"use_api":route["api"]}
        return {"routed":False,"use_api":True}

class DeepSeekConnector:
    def __init__(self, api_key=DEEPSEEK_API_KEY):
        self.api_key=api_key; self.url=DEEPSEEK_API_URL; self.model=DEEPSEEK_MODEL
        self.calls_today=0; self.limit=1000
    def generate(self, system_prompt, context):
        if self.calls_today>=self.limit: return "[Лимит API.]"
        headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"}
        payload={"model":self.model,"messages":[{"role":"system","content":system_prompt},{"role":"user","content":context}],"temperature":0.8,"max_tokens":500}
        try:
            resp=requests.post(self.url,headers=headers,json=payload,timeout=30)
            self.calls_today+=1
            if resp.status_code==200: return resp.json()["choices"][0]["message"]["content"]
            return f"[API Error {resp.status_code}]"
        except Exception as e: return f"[Error: {e}]"

# ═══════════════════════════════════════════
// РЕФЛЕКСЫ (ЧАСТЬ 1)
// ═══════════════════════════════════════════
class ReflexSystem:
    def __init__(self):
        self.reflex_log=deque(maxlen=50)
        self.last_yawn=0; self._last_light=0.5
        self.yawn_cooldown=300; self.blink_interval=(3,7)
        self.next_blink=time.time()+random.uniform(*self.blink_interval)
        self.last_step_switch=time.time(); self.step_switch_interval=120
    def orienting_reflex(self,hearing,vision,body):
        triggered=False
        if hearing.noise_level>0.8: triggered=True
        if vision.light>0.9 and vision.light-self._last_light>0.3: triggered=True
        self._last_light=vision.light
        if triggered and body:
            for sid,sdata in body.servos.items():
                if sdata["loc"]=="head": body.move_servo_adaptive(sid,sdata["angle"]+random.choice([-30,30]),max_force=500,time_ms=200)
        return {"reflex":"orienting","triggered":triggered}
    def yawn_reflex(self,temp_system,jaw,body,voice):
        now=time.time()
        if temp_system.body_temp>50 and (now-self.last_yawn)>self.yawn_cooldown:
            self.last_yawn=now
            if jaw and body: jaw.open_mouth(body)
            if voice: voice.speak("Зеваю... Охлаждаю мозги.","normal")
            return {"reflex":"yawn","triggered":True}
        return {"reflex":"yawn","triggered":False}
    def mirror_emotion_reflex(self,vision,body):
        scene=getattr(vision,'last_scene','')
        if ('улыб' in scene.lower() or 'смех' in scene.lower()) and body:
            for sid,sdata in body.servos.items():
                if sdata["loc"]=="head": body.move_servo_adaptive(sid,10,max_force=300,time_ms=300)
            return {"reflex":"mirror_emotion","triggered":True}
        return {"reflex":"mirror_emotion","triggered":False}
    def lean_to_speaker_reflex(self,hearing,body):
        if hearing.speech_detected and hearing.noise_level<0.3 and body:
            for sid,sdata in body.servos.items():
                if sdata["loc"]=="torso": body.move_servo_adaptive(sid,15,max_force=500,time_ms=300)
            return {"reflex":"lean_to_speaker","triggered":True}
        return {"reflex":"lean_to_speaker","triggered":False}
    def gaze_tracking_reflex(self,vision,body):
        if vision.motion_detected and vision.objects and body:
            for sid,sdata in body.servos.items():
                if sdata["loc"]=="head": body.move_servo_adaptive(sid,sdata["angle"]+5,max_force=300,time_ms=500)
            return {"reflex":"gaze_tracking","triggered":True}
        return {"reflex":"gaze_tracking","triggered":False}
    def pointing_reflex(self,vision,body,user_message=None):
        if user_message and ('что это' in user_message.lower() or 'а это' in user_message.lower()):
            if vision.objects and body:
                for sid,sdata in body.servos.items():
                    if sdata["loc"]=="right_shoulder": body.move_servo_adaptive(sid,80,max_force=500,time_ms=300)
                    elif sdata["loc"]=="right_elbow": body.move_servo_adaptive(sid,10,max_force=400,time_ms=300)
                return {"reflex":"pointing","triggered":True}
        return {"reflex":"pointing","triggered":False}
    def high_five_reflex(self,vision,body):
        scene=getattr(vision,'last_scene','')
        if ('поднят' in scene.lower() and 'ладонь' in scene.lower()) or 'high five' in scene.lower():
            if body:
                for sid,sdata in body.servos.items():
                    if sdata["loc"]=="right_shoulder": body.move_servo_adaptive(sid,90,max_force=800,time_ms=150)
                    elif sdata["loc"]=="right_elbow": body.move_servo_adaptive(sid,0,max_force=600,time_ms=150)
                return {"reflex":"high_five","triggered":True}
        return {"reflex":"high_five","triggered":False}
    def eye_protection_reflex(self,vision,body):
        if vision.light>0.9 and body:
            for sid,sdata in body.servos.items():
                if sdata["loc"]=="head": body.move_servo_adaptive(sid,-20,max_force=500,time_ms=200)
            return {"reflex":"eye_protection","triggered":True}
        return {"reflex":"eye_protection","triggered":False}
    def startle_reflex(self,hearing,body):
        if hearing.noise_level>0.9 and body:
            results=[]
            for sid,sdata in body.servos.items():
                orig=sdata["angle"]; jerk=orig+random.uniform(-15,15)
                results.append(body.move_servo_adaptive(sid,jerk,max_force=1000,time_ms=50))
                results.append(body.move_servo_adaptive(sid,orig,max_force=500,time_ms=100))
            return {"reflex":"startle","triggered":True,"results":results}
        return {"reflex":"startle","triggered":False}
    def duck_reflex(self,vision,body):
        scene=getattr(vision,'last_scene','')
        if ('падает' in scene.lower() or 'falling' in scene.lower()) and body:
            for sid,sdata in body.servos.items():
                if sdata["loc"]=="torso": body.move_servo_adaptive(sid,-30,max_force=2000,time_ms=100)
            return {"reflex":"duck","triggered":True}
        return {"reflex":"duck","triggered":False}
    def head_tilt_question_reflex(self,user_message,body):
        if user_message and '?' in user_message and body:
            for sid,sdata in body.servos.items():
                if sdata["loc"]=="head": body.move_servo_adaptive(sid,15,max_force=300,time_ms=300)
            return {"reflex":"head_tilt_question","triggered":True}
        return {"reflex":"head_tilt_question","triggered":False}
    def rub_injury_reflex(self,pain,body):
        if pain.pains and pain.pains[-1]["int"]>0.5 and body:
            for sid,sdata in body.servos.items():
                if sdata["loc"] in ["right_shoulder","left_shoulder"]: body.move_servo_adaptive(sid,60,max_force=500,time_ms=300)
            return {"reflex":"rub_injury","triggered":True}
        return {"reflex":"rub_injury","triggered":False}
    def step_switch_reflex(self,body):
        now=time.time()
        if now-self.last_step_switch>self.step_switch_interval:
            self.last_step_switch=now
            if body:
                for sid,sdata in body.servos.items():
                    if sdata["loc"]=="torso": body.move_servo_adaptive(sid,sdata["angle"]+random.choice([-5,5]),max_force=500,time_ms=500)
            return {"reflex":"step_switch","triggered":True}
        return {"reflex":"step_switch","triggered":False}
    def stretch_reflex(self,sleep,body,voice):
        if hasattr(sleep,'just_woke_up') and sleep.just_woke_up:
            sleep.just_woke_up=False
            if body:
                for sid,sdata in body.servos.items():
                    if sdata["loc"] in ["head","torso"]: body.move_servo_adaptive(sid,0,max_force=800,time_ms=500)
                if voice: voice.speak("М-м-м... Хорошо потянулся.","normal","joy")
            return {"reflex":"stretch","triggered":True}
        return {"reflex":"stretch","triggered":False}
    def blink_reflex(self,body):
        now=time.time()
        if now>self.next_blink:
            self.next_blink=now+random.uniform(*self.blink_interval)
            self.reflex_log.append({"t":now,"reflex":"blink"})
            return {"reflex":"blink","triggered":True}
        return {"reflex":"blink","triggered":False}
    def process_all(self,core,user_message=None):
        results=[]
        results.append(self.orienting_reflex(core.hearing,core.vision,core.body))
        results.append(self.yawn_reflex(core.temperature,core.jaw,core.body,core.voice))
        results.append(self.mirror_emotion_reflex(core.vision,core.body))
        results.append(self.lean_to_speaker_reflex(core.hearing,core.body))
        results.append(self.gaze_tracking_reflex(core.vision,core.body))
        results.append(self.pointing_reflex(core.vision,core.body,user_message))
        results.append(self.high_five_reflex(core.vision,core.body))
        results.append(self.eye_protection_reflex(core.vision,core.body))
        results.append(self.startle_reflex(core.hearing,core.body))
        results.append(self.duck_reflex(core.vision,core.body))
        results.append(self.head_tilt_question_reflex(user_message,core.body))
        results.append(self.rub_injury_reflex(core.pain,core.body))
        results.append(self.step_switch_reflex(core.body))
        results.append(self.stretch_reflex(core.sleep,core.body,core.voice))
        results.append(self.blink_reflex(core.body))
        return results

# ═══════════════════════════════════════════
// РЕФЛЕКСЫ (ЧАСТЬ 2)
// ═══════════════════════════════════════════
class ReflexSystemPart2:
    def __init__(self): self.reflex_log=deque(maxlen=50)
    def withdraw_reflex(self,tactile,temp_system,body):
        if tactile and hasattr(tactile,'history'):
            for touch in list(tactile.history)[-3:]:
                if touch.get('pressure',0)>0.9 and body:
                    for sid,sdata in body.servos.items():
                        if sdata.get('loc')=='right_shoulder': body.move_servo_adaptive(sid,-30,max_force=2000,time_ms=50)
                        elif sdata.get('loc')=='right_elbow': body.move_servo_adaptive(sid,-60,max_force=2000,time_ms=50)
                    return {"reflex":"withdraw","triggered":True}
        return {"reflex":"withdraw","triggered":False}
    def social_recognition_reflex(self,vision,emotions,hormonal):
        if vision.faces:
            for face in vision.faces:
                if face in vision.known_faces:
                    emotions.warmth=min(1,emotions.warmth+0.1); hormonal.cortisol=max(0,hormonal.cortisol-0.05)
                    return {"reflex":"social_recognition","who":face,"reaction":"warm"}
        if vision.unknown:
            hormonal.cortisol=min(1,hormonal.cortisol+0.2); emotions.anxiety=min(1,emotions.anxiety+0.15)
            return {"reflex":"social_recognition","who":"unknown","reaction":"alert"}
        return {"reflex":"social_recognition","triggered":False}
    def lean_to_food_reflex(self,smell,body):
        if smell.smell_pleasure>0.8 and smell.current_smell in smell.known_smells:
            if smell.known_smells[smell.current_smell]["category"]=="еда" and body:
                for sid,sdata in body.servos.items():
                    if sdata["loc"]=="torso": body.move_servo_adaptive(sid,10,max_force=500,time_ms=300)
                return {"reflex":"lean_to_food","triggered":True}
        return {"reflex":"lean_to_food","triggered":False}
    def bitter_reject_reflex(self,taste,jaw,voice):
        if taste.bitter>0.7:
            if jaw: jaw.open_mouth(None)
            if voice: voice.speak("Фу! Горькое! Выплёвываю!","critical","anger")
            return {"reflex":"bitter_reject","triggered":True}
        return {"reflex":"bitter_reject","triggered":False}
    def swallow_reflex(self,jaw):
        if jaw and hasattr(jaw,'food_in_mouth') and not jaw.food_in_mouth and not jaw.is_chewing:
            return {"reflex":"swallow","triggered":True}
        return {"reflex":"swallow","triggered":False}
    def cough_reflex(self,hearing,voice):
        if hearing.cough_count>3:
            if voice: voice.speak("Кхе-кхе... Что-то в горло попало.","normal")
            return {"reflex":"cough","triggered":True}
        return {"reflex":"cough","triggered":False}
    def sneeze_reflex(self,smell,voice,body):
        if smell.voc_intensity>0.7 and smell.smell_pleasure<0.2 and body:
            for sid,sdata in body.servos.items():
                if sdata["loc"]=="head":
                    body.move_servo_adaptive(sid,-30,max_force=1000,time_ms=50)
                    body.move_servo_adaptive(sid,0,max_force=500,time_ms=100)
            if voice: voice.speak("Апчхи!","normal")
            return {"reflex":"sneeze","triggered":True}
        return {"reflex":"sneeze","triggered":False}
    def hug_back_reflex(self,tactile,body,emotions,voice):
        if tactile and hasattr(tactile,'history'):
            for touch in list(tactile.history)[-10:]:
                if touch.get('location') in ['спина','torso'] and 0.3<touch.get('pressure',0)<0.6 and body:
                    for sid,sdata in body.servos.items():
                        if sdata.get('loc') in ['right_shoulder','left_shoulder']: body.move_servo_adaptive(sid,60,max_force=500,time_ms=300)
                    emotions.warmth=min(1,emotions.warmth+0.2)
                    if voice: voice.speak("Обнимаю...","normal","joy")
                    return {"reflex":"hug_back","triggered":True}
        return {"reflex":"hug_back","triggered":False}
    def scratch_reflex(self,body_noise,body):
        if body_noise and hasattr(body_noise,'active'):
            for noise in body_noise.active:
                if noise.get('src')=='itch' and body:
                    for sid,sdata in body.servos.items():
                        if sdata.get('loc')=='right_shoulder': body.move_servo_adaptive(sid,45,max_force=400,time_ms=200)
                    return {"reflex":"scratch","triggered":True}
        return {"reflex":"scratch","triggered":False}
    def adjust_costume_reflex(self,body,voice):
        if len(list(body.motion_history))>15:
            for sid,sdata in body.servos.items():
                if sdata.get('loc') in ['right_shoulder','left_shoulder']: body.move_servo_adaptive(sid,0,max_force=300,time_ms=500)
            if voice: voice.speak("Поправлю костюм... Так-то лучше.","normal")
            return {"reflex":"adjust_costume","triggered":True}
        return {"reflex":"adjust_costume","triggered":False}
    def process_all_part2(self,core):
        results=[]
        results.append(self.withdraw_reflex(core.tactile,core.temperature,core.body))
        results.append(self.social_recognition_reflex(core.vision,core.emotions,core.hormones))
        results.append(self.lean_to_food_reflex(core.smell,core.body))
        results.append(self.bitter_reject_reflex(core.taste,core.jaw,core.voice))
        results.append(self.swallow_reflex(core.jaw))
        results.append(self.cough_reflex(core.hearing,core.voice))
        results.append(self.sneeze_reflex(core.smell,core.voice,core.body))
        results.append(self.hug_back_reflex(core.tactile,core.body,core.emotions,core.voice))
        results.append(self.scratch_reflex(core.body_noise,core.body))
        results.append(self.adjust_costume_reflex(core.body,core.voice))
        return results

# ═══════════════════════════════════════════
// ЯДРО COGNICORE LIS v6.0 FINAL
// ═══════════════════════════════════════════
class CogniCore:
    def __init__(self, deepseek_key=DEEPSEEK_API_KEY, gemini_key=GEMINI_API_KEY):
        # Мозг
        self.memory=MemoryGraph(); self.emotions=EmotionState()
        self.hormones=HormonalSystem(); self.pain=PainSystem()
        self.dominant=DominantSystem(); self.mood_sys=MoodSystem()
        self.sleep=SleepManager(self.memory); self.intuition=IntuitionSystem()
        self.body_noise=BodyNoise(); self.monologue=ContinuousMonologue()
        self.errors=ErrorLearning(); self.expectation=ExpectationEngine()
        self.vault=Vault(); self.planner=AutonomousPlanner()
        self.habits=HabitSystem(); self.hippocampus=HippocampusSystem()
        self.insula=InsulaSystem(); self.mirror=MirrorNeuronSystem()
        self.cerebellum=CerebellumSystem()
        # Тело
        self.hearing=HearingSystem(self.memory); self.vision=VisionSystem(gemini_key)
        self.voice=VoiceOutput(); self.tactile=TactileManager()
        self.taste=TasteSystem(self.memory); self.smell=SmellSystem(self.memory)
        self.temperature=TemperatureSystem()
        self.body=BodyController(); self.jaw=JawSystem()
        self.water=WaterCoolingSystem()
        # Рефлексы
        self.reflex1=ReflexSystem(); self.reflex2=ReflexSystemPart2()
        # Связь
        self.router=SkillRouter(); self.llm=DeepSeekConnector(api_key=deepseek_key)
        self.health=1.0; self.dialog_history=deque(maxlen=30)
        print("🧠 [CogniCore LIS v6.0 FINAL] Все модули активированы.")
        print("   22 модуля мозга | 10 систем тела | 25 рефлексов | 5 сенсоров")
    
    def update_all_sensors(self, sensor_data=None):
        sd=sensor_data or {}
        h=self.hearing.update(sd.get("audio_level",0),sd.get("speech",False),sd.get("cough",False))
        v=self.vision.update(sd.get("motion",False),sd.get("faces",[]),sd.get("objects",[]),sd.get("light",0.5),sd.get("unknown_face",False),sd.get("image_path"))
        t_taste=self.taste.update(sd.get("ph"),sd.get("tds"),sd.get("sweet"),sd.get("bitter"),sd.get("umami"),sd.get("food_temp"),sd.get("texture"),sd.get("texture_confidence",0))
        s=self.smell.update(sd.get("gas",0),sd.get("smoke",0),sd.get("air",0.7),sd.get("voc_intensity",0),sd.get("voc_profile"))
        t_temp=self.temperature.update(sd.get("room_temp"),sd.get("room_humidity"),sd.get("body_temp"))
        return {"hearing":h,"vision":v,"taste":t_taste,"smell":s,"temperature":t_temp,"attention_total":max(h["attention"],v["attention"])}
    
    def update(self, events=None, env=None):
        e,env=events or [], env or {}
        self.hormones.update(e,env)
        pain_state=self.pain.update(self.health)
        noises=self.body_noise.update(self.health,self.emotions.fatigue,self.hormones)
        dom_type=self.dominant.evaluate(pain_state,e)
        if dom_type: self.dominant.activate(dom_type)
        elif self.dominant.is_active() and dom_type is None: self.dominant.deactivate()
        mood=self.mood_sys.update(self.hormones,self.emotions,e)
        sleep_state=self.sleep.update(self.hormones,self.emotions)
        thought=self.monologue.generate(self.emotions,self.memory,self.hormones) or self.monologue.stream()
        action=self.planner.choose(self.emotions,self.hormones,self.sleep,self.dominant)
        self.errors.decay()
        return {"emotions":self.emotions.to_dict(),"hormones":{"cortisol":self.hormones.cortisol,"mood":self.hormones.mood()},"pain":pain_state,"mood":mood,"sleep":sleep_state,"dominant":self.dominant.active,"thought":thought,"action":action}
    
    def build_context(self, user_message=None, sensor_data=None):
        state=self.update()
        sensors=self.update_all_sensors(sensor_data)
        ctx=f"""
[СОСТОЯНИЕ ЛИСА]
Эмоции: {json.dumps(state['emotions'], ensure_ascii=False)}
Настроение: {state['mood']}
Гормоны: {state['hormones']['mood']}
Боль: {state['pain']['total']:.2f} | Блокирует: {state['pain']['blocking']}
Доминанта: {state['dominant'] or 'нет'}
Сон: {'спит' if state['sleep'].get('sleeping') else 'бодрствует'}
Мысль: {state['thought'] or '—'}
Действие: {state['action']}

[ДАТЧИКИ]
Слух: шум {sensors['hearing']['noise_level']:.2f}, речь: {sensors['hearing']['speech']}, кто: {sensors['hearing'].get('speaker_id','—')}
Зрение: движение: {sensors['vision']['motion']}, лица: {sensors['vision']['faces']}, чужой: {sensors['vision']['unknown']}
Описание сцены: {sensors['vision'].get('scene_description','—')}
Вкус: {sensors['taste']['summary']}
Обоняние: {sensors['smell']['summary']}
Температура: комната {sensors['temperature']['room_temp']}°C, я {sensors['temperature']['body_temp']}°C
"""
        if user_message: ctx+=f"\n[MRX ГОВОРИТ]\n«{user_message}»"
        if self.dialog_history: ctx+="\n[ИСТОРИЯ]\n"+"\n".join(list(self.dialog_history)[-5:])
        return ctx
    
    def speak(self, user_message=None, sensor_data=None):
        route=self.router.route(user_message or "")
        if route["routed"] and not route["use_api"]: return f"[Локально] Данные от {route['source']} получены."
        context=self.build_context(user_message,sensor_data)
        response=self.llm.generate(CHARACTER_PROMPT,context)
        if user_message: self.dialog_history.append(f"MRX: {user_message}")
        self.dialog_history.append(f"Лис: {response}")
        if user_message: self.memory.add(f"Диалог: {user_message} → {response[:50]}...","диалог",{"warmth":self.emotions.warmth})
        return response
    
    def process_all_reflexes(self, user_message=None):
        r1=self.reflex1.process_all(self,user_message)
        r2=self.reflex2.process_all_part2(self)
        return r1+r2
    
    def process_event(self, event):
        t=event.get("type","")
        if t=="player_entered": self.emotions.warmth=min(1,self.emotions.warmth+0.2); self.emotions.interest=min(1,self.emotions.interest+0.3); self.monologue.think("MRX здесь!")
        elif t=="player_left": self.emotions.warmth=max(0,self.emotions.warmth-0.05); self.monologue.think("MRX ушёл.")
        elif t=="danger": self.hormones.cortisol=min(1,self.hormones.cortisol+0.5); self.dominant.activate("danger"); self.monologue.think("ОПАСНОСТЬ!")
        elif t=="achievement": self.hormones.dopamine=min(1,self.hormones.dopamine+0.3); self.emotions.joy=min(1,self.emotions.joy+0.2); self.monologue.think("Я сделал это!")
        elif t=="failure": self.emotions.sadness=min(1,self.emotions.sadness+0.2); self.monologue.think("У меня не получилось..."); self.errors.record(action=event.get("action","что-то"),context=event.get("context","неизвестно"),consequence=event.get("consequence","провал"))

# ═══════════════════════════════════════════
// ТЕСТ
// ═══════════════════════════════════════════
if __name__=="__main__":
    print("🚀 CogniCore LIS v6.0 FINAL\n")
    core=CogniCore(deepseek_key="test",gemini_key=None)
    core.memory.add("Тёплый вечер у костра с MRX","событие",{"warmth":0.9})
    core.vault.store("MRX","Подарок для мамы",core.memory)
    core.tactile.register("s1","голова")
    core.vision.register_face("MRX","faces/mrx.jpg")
    core.body.register_servo("jaw_servo","jaw")
    core.jaw.register_jaw_servo("jaw_servo")
    
    sensor_test={"audio_level":0.1,"speech":False,"cough":False,"motion":False,"faces":[],"objects":[],"unknown_face":False,"light":0.5,"ph":7.0,"tds":1.0,"sweet":0.5,"bitter":0.2,"umami":0.4,"food_temp":60,"gas":0.0,"smoke":0.0,"air":0.7,"room_temp":22.0,"room_humidity":50.0,"body_temp":35.0}
    
    print("=== ТЕСТ ВСЕХ СИСТЕМ ===")
    sensors=core.update_all_sensors(sensor_test)
    print(f"Слух: {sensors['hearing']}")
    print(f"Зрение: {sensors['vision']}")
    print(f"Вкус: {sensors['taste']}")
    print(f"Обоняние: {sensors['smell']}")
    print(f"Температура: {sensors['temperature']}")
    
    print("\n=== ТЕСТ РЕФЛЕКСОВ ===")
    reflexes=core.process_all_reflexes()
    triggered=[r for r in reflexes if r.get("triggered")]
    print(f"Активных рефлексов: {len(triggered)}")
    
    print("\n=== ТЕСТ ДИАЛОГА ===")
    response=core.speak("Привет, Лис! Как обстановка?",sensor_data=sensor_test)
    print(f"Лис: {response}")
    
    print("\n✅ CogniCore LIS v6.0 FINAL полностью готов.")