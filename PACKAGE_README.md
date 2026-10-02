# CyberWarEnv — Defensive Research & Simulation Environment v2.0.0

بيئة بحثية دفاعية لمحاكاة الدفاع السيبراني الذاتي (Autonomous Cyber Defense)
باستخدام التعلم المعزز العميق — **لأغراض بحثية دفاعية فقط**، بدون أي أدوات
اختراق حقيقية.

A Gymnasium-compatible defensive cyber simulation for studying how Deep RL
defenders learn containment policies under partial observability, sensor
noise, and adaptive abstract attackers.

## المكونات / Components

| الملف | الوصف |
|---|---|
| `cyberwarenv/topology.py` | مولدات الطوبولوجيا (Corporate 18-node / DataCenter 20-node) مع مناطق وأصول حرجة وفخاخ |
| `cyberwarenv/attack.py` | مهاجمون مجردون احتماليون: Scripted / Probabilistic / Adaptive |
| `cyberwarenv/sensors.py` | نموذج إدراك جزئي: 3 إعدادات حساسات (A/B/C) مع إنذارات كاذبة/فائتة |
| `cyberwarenv/env.py` | بيئة Gymnasium: 9 أفعال دفاعية باستهداف تلقائي (SOC triage) + محرك مكافآت |
| `cyberwarenv/tracking.py` | سجل تجارب مع provenance كامل (SHA-256، بذور، hashes إعدادات) |
| `cyberwarenv/stats.py` | المحرك الإحصائي: Bootstrap CI، Wilcoxon، Mann-Whitney، Cohen's d، Holm-Bonferroni |

## الأفعال الدفاعية / Defensive Actions

```
monitor · increase_monitoring · isolate · contain · remediate
patch · restrict · deploy_decoy · wait
```

كل فعل يُطبق تلقائيًا على العقدة الأكثر شبهة (أعلى EMA للإنذارات + الحرجية)
— تجريد لسير عمل محلل SOC.

## التثبيت / Install

```bash
pip install -r requirements.txt
```

## التشغيل / Reproduce

```bash
# 1) اختبار سريع (30 ثانية)
python3 scripts/quick_test.py

# 2) معايرة الصعوبة (Calibration Sweep)
python3 scripts/calibrate.py

# 3) التحقق الكامل (20 تشغيل × 100k خطوة — موزع على عمليتين)
python3 scripts/verify_full.py --cells 0,2 --experiment-id EXP-2026-000001 &
python3 scripts/verify_full.py --cells 1,3 --experiment-id EXP-2026-000002 &

# 4) التحليل الإحصائي + الرسوم
python3 scripts/analyze.py
python3 scripts/figures.py
```

## الاستخدام البرمجي / Quick Start

```python
from cyberwarenv import CyberWarEnv, DifficultyProfile

env = CyberWarEnv(
    scenario="corporate",          # أو "datacenter"
    attacker_kind="scripted",      # scripted | probabilistic | adaptive
    difficulty=DifficultyProfile(),
    topology_seed=100,
    env_seed=0,
)
obs, info = env.reset(seed=42)
obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
print(info["episode_metrics"])
```

## ملاحظة علمية / Scientific Note

أرقام الورقة المرجعية (82.6% / 85.1% / 68.9%) تُعامل كـ **LEGACY CLAIMS** —
لا تُعتبر نتائج مُتحققة إلا بعد إعادة إنتاجها داخل بيئة موثقة ومعايرة.
كل نتيجة ينتجها هذا الكود تحمل سلسلة provenance كاملة.

## الأخلاقيات / Ethics

هذه البيئة محاكاة دفاعية مجردة. لا تحتوي ولا تنتج أي أدوات هجومية حقيقية.
المهاجمون سياسات احتمالية مجردة على أفعال مجردة (Reconnaissance، Lateral
Movement، ...) بلا أي منطق اختراق تشغيلي.
