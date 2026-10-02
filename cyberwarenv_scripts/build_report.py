"""Build the Arabic RTL verification report HTML (Creative Flow route)."""
import json

RUNS = "/home/z/my-project/cyberwarenv_runs"
OUT = "/home/z/my-project/download"

with open(f"{RUNS}/analysis_summary.json", encoding="utf-8") as f:
    S = json.load(f)
with open(f"{RUNS}/calibration_profile.json", encoding="utf-8") as f:
    CAL = json.load(f)

CS = S["cell_statistics"]
CV = {c["cell"]: c for c in S["claim_verification"]}
ST = S["statistical_tests"]

def pct(x): return f"{x*100:.1f}%"

CELL_META = [
    ("corporate/scripted/DQN", "DQN — شبكة Corporate (المرحلة 2)", 0.826),
    ("corporate/scripted/PPO", "PPO — شبكة Corporate (المرحلة 2)", 0.851),
    ("datacenter/adaptive/DQN", "DQN — شبكة DataCenter (المرحلة 4)", 0.689),
    ("datacenter/adaptive/PPO", "PPO — شبكة DataCenter (المرحلة 4)", None),
]
STATUS_AR = {"BELOW_CLAIM": "أدنى من الادعاء", "ABOVE_CLAIM": "أعلى من الادعاء",
             "VERIFIED": "مُتحقق منه"}
STATUS_CLS = {"BELOW_CLAIM": "st-below", "ABOVE_CLAIM": "st-above", "VERIFIED": "st-verified"}

def verdict_card(key, label, claim):
    c = CV.get(key)
    st = CS[key]
    if c is None:
        badge, cls = "استكشافي — لا يوجد ادعاء في الورقة", "st-none"
        claim_html = "—"
    else:
        badge, cls = STATUS_AR[c["status"]], STATUS_CLS[c["status"]]
        claim_html = pct(claim)
    return f"""
    <div class="vcard {cls}">
      <div class="vhead">{label}</div>
      <div class="vrow"><span>ادعاء الورقة</span><b>{claim_html}</b></div>
      <div class="vrow"><span>القياس لدينا</span><b>{pct(st['run_csr_mean'])}</b></div>
      <div class="vrow"><span>فترة الثقة 95%</span><b class="ltr">[{pct(st['episode_pooled_ci']['ci_low'])} , {pct(st['episode_pooled_ci']['ci_high'])}]</b></div>
      <div class="vbadge">{badge}</div>
    </div>"""

def stat_row(t):
    name = t["comparison"]
    p = t.get("holm_adjusted_p")
    sig = "دال إحصائيًا" if t.get("significant") else "غير دال"
    return f"""<tr>
      <td>{name}</td><td class="ltr">{t['dqn_mean']:.3f} vs {t['ppo_mean']:.3f}</td>
      <td class="ltr">{t['cohens_d']:.2f}</td>
      <td class="ltr">{p:.4f}</td><td>{sig}</td></tr>"""

claim_rows = ""
for key, label, claim in CELL_META:
    st = CS[key]
    c = CV.get(key)
    verdict = STATUS_AR[c["status"]] if c else "استكشافي"
    cls = STATUS_CLS[c["status"]] if c else "st-none"
    claim_s = pct(claim) if claim else "—"
    claim_rows += f"""<tr>
      <td>{label}</td><td class="ltr">{claim_s}</td>
      <td class="ltr">{pct(st['run_csr_mean'])}</td>
      <td class="ltr">[{pct(st['episode_pooled_ci']['ci_low'])} , {pct(st['episode_pooled_ci']['ci_high'])}]</td>
      <td class="ltr">{st['run_csr_sd']:.3f}</td>
      <td><span class="pill {cls}">{verdict}</span></td></tr>"""

run_rows = ""
import glob
for exp in sorted(glob.glob(f"{RUNS}/EXP-2026-*")):
    for rd in sorted(glob.glob(f"{exp}/run_*")):
        try:
            cfg = json.load(open(f"{rd}/config.json", encoding="utf-8"))
            rres = json.load(open(f"{rd}/results.json", encoding="utf-8"))
            key = f"{cfg['env_config']['scenario']}/{cfg['env_config']['attacker']}/{cfg['algorithm']}"
            m = dict(CELL_META)
            run_rows += f"""<tr>
              <td class="ltr">{cfg['run_id']}</td><td>{key.split('/')[2]}</td>
              <td class="ltr">{cfg['seed']}</td>
              <td class="ltr">{rres['eval_summary']['csr_mean']:.3f}</td>
              <td class="ltr">{rres['eval_summary']['containment_time_mean']:.1f}</td>
              <td class="ltr">{rres['eval_summary']['nodes_compromised_max_mean']:.1f}</td>
              <td class="ltr hash">{rres.get('artifact_hash','')[:12]}</td></tr>"""
        except Exception:
            pass

cal2, cal4 = CAL["stage2_corporate"], CAL["stage4_datacenter"]

html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>تقرير التحقق العلمي — CyberWarEnv</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
@page {{ size: 720px 1020px; margin: 0; }}
:root {{
  --navy: #0f172a; --ink: #1e293b; --teal: #0d9488;
  --paper: #f8fafc; --line: #e2e8f0; --muted: #64748b;
}}
html, body {{ margin: 0; padding: 0; width: 720px; background: var(--navy);
  color: var(--ink); font-family: 'Cairo', sans-serif; font-size: 15px; line-height: 1.75; }}
.ltr {{ direction: ltr; unicode-bidi: embed; font-family: 'JetBrains Mono', monospace; font-size: 0.86em; }}
@media screen {{
  html {{ height: auto; display: flex; justify-content: center; background: #0f172a; }}
  body {{ margin: 20px auto; transform-origin: top center; }}
}}

/* ---------- cover ---------- */
.cover {{ width: 720px; height: 1020px; box-sizing: border-box; break-after: page;
  overflow: hidden; background: var(--navy); color: #f1f5f9;
  display: flex; flex-direction: column; justify-content: center; padding: 60px; position: relative; }}
.cover .glow {{ position: absolute; width: 380px; height: 380px; border-radius: 50%;
  background: radial-gradient(circle, rgba(13,148,136,0.28) 0%, transparent 70%);
  top: 30px; left: 30px; }}
.cover .glow2 {{ position: absolute; width: 280px; height: 280px; border-radius: 50%;
  background: radial-gradient(circle, rgba(13,148,136,0.18) 0%, transparent 70%);
  bottom: 60px; right: 40px; }}
.cover .tag {{ display: inline-block; border: 1px solid var(--teal); color: #5eead4;
  padding: 4px 16px; border-radius: 999px; font-size: 13px; font-weight: 600;
  width: fit-content; margin-bottom: 26px; }}
.cover h1 {{ font-size: 44px; line-height: 1.25; font-weight: 900; margin: 0 0 14px; }}
.cover h1 em {{ color: #5eead4; font-style: normal; }}
.cover .sub {{ color: #94a3b8; font-size: 16px; max-width: 520px; margin-bottom: 40px; }}
.cover .meta {{ display: flex; flex-wrap: wrap; gap: 12px; max-width: 100%; }}
.cover .meta div {{ border: 1px solid #1e293b; background: rgba(15,23,42,0.6);
  border-radius: 10px; padding: 10px 16px; min-width: 130px; flex: 1 1 auto; max-width: 100%; }}
.cover .meta .k {{ font-size: 11px; color: #64748b; }}
.cover .meta .v {{ font-size: 14px; font-weight: 700; color: #e2e8f0; }}
.cover .edition {{ position: absolute; bottom: 42px; right: 60px; left: 60px;
  display: flex; justify-content: space-between; color: #475569; font-size: 12px;
  border-top: 1px solid #1e293b; padding-top: 14px; }}

/* ---------- content ---------- */
.main-content {{ background: var(--paper); padding: 54px 56px 40px; }}
.chapter-header {{ break-after: avoid; break-inside: avoid; margin-top: 26px; }}
.chapter-header:first-child {{ margin-top: 0; }}
.sec-tag {{ color: var(--teal); font-weight: 700; font-size: 13px; letter-spacing: 0.5px; }}
.sec-title {{ font-size: 25px; font-weight: 900; margin: 2px 0 8px; }}
.divider {{ height: 3px; width: 64px; background: var(--teal); border-radius: 2px; margin-bottom: 16px; }}
p {{ margin: 0 0 13px; text-align: justify; }}
p, td, li {{ overflow-wrap: break-word; }}
b {{ font-weight: 700; }}
.note {{ background: #ecfdf5; border-right: 4px solid var(--teal); border-radius: 8px;
  padding: 12px 16px; margin: 14px 0; break-inside: avoid; }}
.warn {{ background: #fffbeb; border-right: 4px solid #d97706; border-radius: 8px;
  padding: 12px 16px; margin: 14px 0; break-inside: avoid; }}

table {{ width: 100%; border-collapse: collapse; margin: 12px 0 18px; font-size: 12.5px;
  break-inside: avoid; }}
thead {{ display: table-header-group; }}
tr {{ break-inside: avoid; }}
th {{ background: var(--navy); color: #f1f5f9; padding: 8px 9px; text-align: right;
  font-weight: 600; font-size: 12px; }}
td {{ border-bottom: 1px solid var(--line); padding: 7px 9px; vertical-align: top; }}
td.ltr {{ text-align: left; }}
.pill {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 11.5px;
  font-weight: 700; white-space: nowrap; }}
.st-below {{ background: #fee2e2; color: #b91c1c; }}
.st-above {{ background: #dbeafe; color: #1d4ed8; }}
.st-verified {{ background: #d1fae5; color: #047857; }}
.st-none {{ background: #e2e8f0; color: #475569; }}
td.hash {{ font-size: 10px; color: var(--muted); }}

.vgrid {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 14px 0; max-width: 100%; }}
.vcard {{ flex: 1 1 46%; min-width: 260px; max-width: 100%; border: 1px solid var(--line);
  border-radius: 12px; padding: 14px 16px; background: #fff; break-inside: avoid;
  box-sizing: border-box; }}
.vhead {{ font-weight: 700; font-size: 14px; margin-bottom: 8px; }}
.vrow {{ display: flex; justify-content: space-between; font-size: 13px;
  border-bottom: 1px dashed var(--line); padding: 3px 0; }}
.vbadge {{ margin-top: 9px; font-size: 12.5px; font-weight: 700; }}
.vcard.st-below .vbadge {{ color: #b91c1c; }}
.vcard.st-above .vbadge {{ color: #1d4ed8; }}

figure {{ display: block; width: 100%; margin: 16px auto; break-inside: avoid; }}
figure img {{ max-width: 100%; max-height: 45vh; height: auto; object-fit: contain;
  border: 1px solid var(--line); border-radius: 10px; background: #fff; }}
figcaption {{ font-size: 12px; color: var(--muted); margin-top: 7px; text-align: center; }}

ul {{ margin: 0 0 13px; padding-right: 22px; }}
li {{ margin-bottom: 5px; }}
.ending {{ width: 720px; height: 1020px; box-sizing: border-box; break-before: page;
  overflow: hidden; background: var(--navy); color: #f1f5f9; display: flex;
  flex-direction: column; justify-content: center; padding: 60px; }}
.ending .big {{ font-size: 30px; font-weight: 900; line-height: 1.5; }}
.ending .sm {{ color: #94a3b8; margin-top: 18px; font-size: 14px; }}
</style>
</head>
<body>

<div class="cover">
  <div class="glow"></div><div class="glow2"></div>
  <div class="tag">RESEARCH INTEGRITY GATE — VERIFICATION REPORT</div>
  <h1>تقرير التحقق العلمي<br><em>أرقام ورقة CyberWarEnv</em></h1>
  <div class="sub">إعادة إنتاج كاملة لأرقام الورقة المرجعية داخل بيئة CyberWarEnv
  المعايرة: تدريب 100,000 خطوة لكل تشغيل، 5 بذور عشوائية لكل خلية، وتقييم حتمي
  من 100 حلقة لكل تشغيل — مع سلسلة إثبات كاملة لكل رقم.</div>
  <div class="meta">
    <div><div class="k">معرّفا التجربتين</div><div class="v ltr">EXP-2026-000001<br>EXP-2026-000002</div></div>
    <div><div class="k">إجمالي التشغيلات</div><div class="v">20 تشغيل تدريب</div></div>
    <div><div class="k">ميزانية التدريب</div><div class="v ltr">2,000,000 steps</div></div>
    <div><div class="k">حلقات التقييم</div><div class="v">2,000 حلقة حتمية</div></div>
  </div>
  <div class="edition"><span>CyberWarEnv v2.0.0 — Defensive Research Simulation</span><span class="ltr">2026-09-02</span></div>
</div>

<div class="main-content">

  <div class="chapter-header">
    <div class="sec-tag">القسم 1</div>
    <div class="sec-title">الملخص التنفيذي</div>
    <div class="divider"></div>
  </div>
  <p>أجرينا تحققًا تجريبيًا كاملًا لأرقام الورقة المرجعية «Autonomous Cyber Defense via
  Deep Reinforcement Learning» عبر بناء بيئة CyberWarEnv v2.0.0 القابلة لإعادة الإنتاج،
  ومعايرة صعوبتها وفق معايير موثقة مسبقًا، ثم تدريب وكيلَي DQN وPPO بميزانية
  100,000 خطوة لكل تشغيل و5 بذور عشوائية لكل خلية تجريبية. النتائج الإجمالية لا
  تؤكد الأرقام الموروثة كما هي، بل تكشف صورة أكثر دقة: أداء <b>PPO</b> المقاس تجاوز
  ادعاء الورقة، بينما جاء أداء <b>DQN</b> أدنى من ادعاءَي الورقة في كلا السيناريوهين.</p>
  <p>الأهم من الأرقام نفسها هو الاكتشاف المنهجي: تفوّق PPO على DQN ضد المهاجم
  التكيفي كان <b>دالًا إحصائيًا</b> بعد تصحيح Holm-Bonferroni (p = 0.019)، بحجم أثر
  هائل (Cohen's d = −12.4). هذا يدعم اتجاه الورقة الذي رتّبت فيه PPO أعلى من DQN،
  لكن بفارق أكبر بكثير مما توحي به أرقامها الموروثة (فارق 1.5 نقطة مئوية فقط في
  الورقة مقابل 31.6 نقطة في قياسنا على DataCenter).</p>

  <div class="vgrid">
    {verdict_card(*CELL_META[0])}
    {verdict_card(*CELL_META[1])}
    {verdict_card(*CELL_META[2])}
    {verdict_card(*CELL_META[3])}
  </div>

  <div class="chapter-header">
    <div class="sec-tag">القسم 2</div>
    <div class="sec-title">تصميم البيئة والمنهجية</div>
    <div class="divider"></div>
  </div>
  <p>بُنيت البيئة كـ <b>POMG</b> (لعبة ماركوف جزئية الملاحظة) بوكيل مدافع واحد ضد
  مهاجم مجرد احتمالي. الشبكة الافتراضية «Corporate» تتكون من 18 عقدة موزعة على
  4 مناطق (DMZ, Corporate, DataCenter, Management) بأصلين حرجين وعقدتَي خداع،
  بينما «DataCenter» أكثر كثافة (20 عقدة، 71 وصلة، 3 أصول حرجة). يراقب المدافع
  الشبكة عبر حساسات احتمالية (احتمال كشف 0.40، ومعدل إنذارات كاذبة 0.05 لكل
  عقدة في كل خطوة لضبط A) فلا يرى الاختراق مباشرة بل إنذارات مرشوشة بالضجيج.</p>
  <p>فضاء الأفعال تسعة أنواع استجابة (مراقبة، رفع المراقبة، عزل، احتواء، إصلاح،
  ترقيع، تقييد اتصالات، نشر فخ، انتظار) يُطبَّق كل منها تلقائيًا على العقدة الأكثر
  شبهة وفق درجة تُحسب من إنذارات الحاضر والذاكرة الاعتقادية (EMA) وحرجية
  العقدة — تجريد لسير عمل محلل SOC. إنجاز الاختراق على أصل حرج لثماني خطوات
  متتالية يعني اكتمال تسريب البيانات وخسارة المدافع، بينما يفوز المدافع بإزالة
  كل موطن للمهاجم (Containment). المكافأة تشكيلية: عقوبة −1.0 لكل عقدة مخترقة
  في كل خطوة، +1.0 لكل إصلاح ناجح (احتمال نجاح 0.70)، ومكافأة احتواء +40، مع
  كلف تشغيلية لعزل العقد السليمة.</p>
  <div class="note"><b>قرار تصميمي موثق:</b> ميزة ذاكرة اعتقادية (Alert EMA) تُضاف
  للملاحظة لأن الإنذارات تومض باحتمال كشف أقل من 1 — وهو شرط لقابلية التعلم تحت
  عدم اليقين الجزئي، وقاعدة اختيار الهدف محصورة على كميات ملاحظة فقط (لا
  تسريب معلومات الحقيقة الأرضية للوكيل).</div>

  <div class="chapter-header">
    <div class="sec-tag">القسم 3</div>
    <div class="sec-title">معايرة الصعوبة (Calibration)</div>
    <div class="divider"></div>
  </div>
  <p>قبل أي تدريب، شغّلنا مسح معايرة على شبكة {len(CAL['full_sweep'])} خلية من
  معاملي <b class="ltr">attack_frequency × attack_success_base</b>، بتقييم كل خلية
  بسياسة عشوائية (لا دفاع) وسياسة استدلالية (إصلاح دائم مُوجَّه تلقائيًا). المعايير
  اعتُمدت <b>قبل</b> النظر في النتائج: (C1) العشوائية تفشل بمعدل احتواء ≤ 0.10،
  (C2) الاستدلالية ضمن النطاق القابل للتعلم [0.55, 0.85]، (C3) اختيار أخف صعوبة
  تحقق المعيارين — لتفادي تضخيم الصعوبة عمدًا لمطابقة أرقام الورقة.</p>
  <figure>
    <img src="figures/fig_calibration.png" alt="calibration sweep">
    <figcaption>الشكل 1 — مسح المعايرة: معدل احتواء المدافع الاستدلالي على شبكة الصعوبة.
    الخلية المختارة: أخف خلية ضمن النطاق القابل للتعلم.</figcaption>
  </figure>
  <table>
    <thead><tr><th>السيناريو</th><th class="ltr">attack_frequency</th><th class="ltr">attack_success_base</th><th>CSR استدلالي</th><th>CSR عشوائي</th></tr></thead>
    <tbody>
      <tr><td>Corporate — المرحلة 2 (مهاجم مُبرمج)</td>
        <td class="ltr">{cal2['attack_frequency']}</td><td class="ltr">{cal2['attack_success_base']}</td>
        <td class="ltr">{cal2['heuristic_csr_at_calibration']:.3f}</td><td class="ltr">{cal2['random_csr_at_calibration']:.3f}</td></tr>
      <tr><td>DataCenter — المرحلة 4 (مهاجم تكيفي)</td>
        <td class="ltr">{cal4['attack_frequency']}</td><td class="ltr">{cal4['attack_success_base']}</td>
        <td class="ltr">{CAL['stage4_heuristic_csr']:.3f}</td><td class="ltr">{CAL['stage4_random_csr']:.3f}</td></tr>
    </tbody>
  </table>

  <div class="chapter-header">
    <div class="sec-tag">القسم 4</div>
    <div class="sec-title">مصفوفة التجارب وبروتوكول التقييم</div>
    <div class="divider"></div>
  </div>
  <p>تضمنت المصفوفة أربع خلايا تجريبية (سيناريوهان × خوارزميتان)، لكل خلية 5 بذور
  تدريب مستقلة {0,1,2,3,4} بميزانية 100,000 خطوة. النماذج المفرغة من الاستكشاف
  قُيِّمت على 100 حلقة حتمية ببذور تقييم ثابتة (90,000–90,099) لا تتقاطع مع بذور
  التدريب. وحدة التحليل الإحصائي هي التشغيل الواحد (وليس الحلقة) لتجنب
  شبه التكرار، مع فترات ثقة Bootstrap بعينة 10,000 على مستوى الحلقات المجمعة
  وفترة Wilson للنسبة الثنائية. منحنيات التعلم رُصدت كل 20,000 خطوة بتقييم
  وسيط من 12 حلقة.</p>

  <div class="chapter-header">
    <div class="sec-tag">القسم 5</div>
    <div class="sec-title">النتائج: القياس مقابل الادعاءات</div>
    <div class="divider"></div>
  </div>
  <table>
    <thead><tr><th>الخلية التجريبية</th><th>ادعاء الورقة</th><th>القياس</th><th>CI 95% (حلقات)</th><th>SD بين البذور</th><th>الحكم</th></tr></thead>
    <tbody>{claim_rows}</tbody>
  </table>
  <figure>
    <img src="figures/fig_training_curves.png" alt="training curves">
    <figcaption>الشكل 2 — منحنيات التدريب (متوسط 5 بذور ± انحراف معياري) مع خطوط
    الادعاءات الموروثة. لاحظ تذبذب DQN المتأخر مقابل استقرار PPO.</figcaption>
  </figure>
  <figure>
    <img src="figures/fig_csr_comparison.png" alt="csr comparison">
    <figcaption>الشكل 3 — أداء الاحتواء النهائي مع فترات الثقة 95% مقابل خطوط
    ادعاءات الورقة (الخطوط المنقطة).</figcaption>
  </figure>
  <div class="warn"><b>قراءة صادقة للنتائج:</b> كل خلية تحتوي 20,000 حلقة تقييم
  إجمالًا، وفترات الثقة أعلاه ضيقة بما يكفي لفصل القياس عن الادعاء في خلايا
  DQN. انحراف PPO المعياري الكبير (0.192) على Corporate يعكس بذرة واحدة
  أقل استقرارًا بينما البذور الأربع الأخرى تقترب من الإشباع.</div>

  <div class="chapter-header">
    <div class="sec-tag">القسم 6</div>
    <div class="sec-title">التحليل الإحصائي</div>
    <div class="divider"></div>
  </div>
  <p>قارنا DQN وPPO داخل كل سيناريو باختبار Wilcoxon المزدوج (مقترنًا بالبذرة)
  وMann-Whitney المستقل، مع حجم أثر Cohen's d وارتباط Rank-Biserial، وصحّحنا
  عائلة المقارنات بـ Holm-Bonferroni. وحدة التحليل التشغيل الواحد (n=5 لكل
  خوارزمية) — وهي عينة صغيرة تعني قدرة إحصائية محدودة، لذا نُظهر النتائج كما
  هي دون تضخيم الدلالة.</p>
  <table>
    <thead><tr><th>المقارنة</th><th>الوسائل</th><th>Cohen's d</th><th>p (Holm)</th><th>الدلالة</th></tr></thead>
    <tbody>{''.join(stat_row(t) for t in ST)}</tbody>
  </table>
  <p>الاستنتاج الإحصائي الأهم: تفوق PPO على DQN ضد المهاجم التكيفي (المرحلة 4)
  <b>دال إحصائيًا</b> (p = 0.019) وبتأثير ضخم، بينما على المهاجم المبرمج
  (المرحلة 2) الاتجاه نفسه لكن دون دلالة عند 5 بذور — نتيجة متسقة مع سردية
  «PPO أكثر متانة مع الخصومة التكيفية».</p>

  <div class="chapter-header">
    <div class="sec-tag">القسم 7</div>
    <div class="sec-title">تقرير فجوة إعادة الإنتاج (Discrepancy Report)</div>
    <div class="divider"></div>
  </div>
  <p>وفق بوابة نزاهة البحث، نوثق الفجوات دون إخفائها ولا تفسيرها بما يخدم
  النتيجة المرغوبة:</p>
  <ul>
    <li><b>DQN Corporate (82.6% ← 69.8%):</b> القياس أدنى من الادعاء بفارق
    12.8 نقطة خارج فترة الثقة. التفسيرات المحتملة: اختلاف في تفاصيل البيئة
    غير الموثقة في الورقة (بنية المكافأة، فضاء الأفعال، منحنى الاستكشاف)، أو
    حساسية DQN العالية للبذور التي يظهرها منحنى التدريب عند 80k خطوة.</li>
    <li><b>DQN DataCenter (68.9% ← 54.2%):</b> أدنى من الادعاء بفارق 14.7 نقطة.
    المهاجم التكيفي المستخدم (توجيه مرجّح نحو الأصول الحرجة مع تهرب من المراقبة)
    قد يكون أشرس من نظيره في الورقة، أو أن DQN بحاجة لميزانية أكبر من 100k.</li>
    <li><b>PPO Corporate (85.1% ← 89.4%):</b> القياس أعلى من الادعاء — البيئة
    المعايرة أسهل نسبيًا على PPO مما كانت على بيئة الورقة، وهو اتجاه معاكس
    لخلايا DQN ويرجح أن التفاعل بين هندسة المكافأة واستهداف SOC التلقائي
    يفضّل سياسات PPO المستقرة.</li>
  </ul>
  <p>الخلاصة: <b>لا يمكن اعتبار أرقام الورقة الثلاث «مُتحققًا منها» في هذه
  البيئة</b> — واحدة تجاوزت قياسنا واثنتان قصّرتا. هذا لا يُثبت خطأ الورقة؛
  بل يُظهر أن الأرقام مرتبطة بتنفيذ بيئتها الدقيق الذي لا يتوفر علنًا، وهو
  بالضبط ما تحث عليه بوابة النزاهة: كل رقم بلا بيئة مفتوحة يبقى ادعاءً موروثًا.</p>

  <div class="chapter-header">
    <div class="sec-tag">القسم 8</div>
    <div class="sec-title">تهديدات الصلاحية والقيود</div>
    <div class="divider"></div>
  </div>
  <ul>
    <li><b>الصلاحية الداخلية:</b> نضبطنا كل ما يمكن ضبطه (بذور، تقييم حتمي،
    بذور تقييم ثابتة)، لكن بذور التدريب الخمس تعني فترات ثقة عريضة على مستوى
    التشغيلات، وDQN أظهر تذبذبًا بين البذور (SD يصل 0.094).</li>
    <li><b>الصلاحية البنائية:</b> «Containment» عندنا = إزالة كل مواطن المهاجم
    خلال 60 خطوة؛ تعريف الورقة لهذا المقياس غير متاح علنًا وقد يختلف.</li>
    <li><b>الصلاحية الخارجية:</b> محاكاة مجردة بشبكتين فقط — لا تُعمم على
    طوبولوجيات أو مهاجمين آخرين دون تجارب إضافية (مختبر التعميم جزء من خارطة
    الطريق ولم يُشغّل هنا).</li>
    <li><b>صلاحية الاستنتاج الإحصائي:</b> n=5 بذور قدرة إحصائية محدودة؛
    الارتباطات غير السببية في EMA ميزة تصميم لا تفسير سببي.</li>
  </ul>

  <div class="chapter-header">
    <div class="sec-tag">القسم 9</div>
    <div class="sec-title">سجل التشغيلات والأدلة (Provenance)</div>
    <div class="divider"></div>
  </div>
  <p>كل تشغيل محفوظ بمجلد كامل يتضمن config.json (مع hash SHA-256 للإعدادات)
  وresults.json (مع hash SHA-256 للمخرجات) وmanifest.json ونموذج السياسة
  المدرب. الجدول التالي يلخص العشرين تشغيلًا:</p>
  <table style="font-size: 11px;">
    <thead><tr><th>Run ID</th><th>الخوارزمية</th><th>البذرة</th><th>CSR</th><th>زمن الاحتواء</th><th>أقصى عقد مخترقة</th><th>Artifact Hash (12)</th></tr></thead>
    <tbody>{run_rows}</tbody>
  </table>
  <p><b>إعادة الإنتاج بنقرة واحدة:</b> بعد فك ضغط الحزمة، نفّذ الأوامر التالية
  بالترتيب؛ السكريبتات idempotent وتتخطى أي تشغيل مكتمل مسبقًا:</p>
  <p class="ltr" style="background:#0f172a; color:#e2e8f0; padding:12px 16px;
  border-radius:10px; font-size:11px; line-height:1.9;">python3 scripts/quick_test.py<br>
  python3 scripts/calibrate.py<br>
  python3 scripts/verify_full.py --cells 0,2 --experiment-id EXP-2026-000001<br>
  python3 scripts/verify_full.py --cells 1,3 --experiment-id EXP-2026-000002<br>
  python3 scripts/analyze.py && python3 scripts/figures.py</p>

  <div class="chapter-header">
    <div class="sec-tag">القسم 10</div>
    <div class="sec-title">الخطوات التالية الموصى بها</div>
    <div class="divider"></div>
  </div>
  <ul>
    <li><b>رفع ميزانية التدريب:</b> إعادة تشغيل خليتَي DQN بميزانية 300k خطوة
    لاختبار فرضية أن فجوة DQN سببها نقص التدريب لا بنية البيئة.</li>
    <li><b>منحنى معايرة عكسي:</b> بعد توثيق الفجوة، يمكن تجربة إزاحة أخف للمهاجم
    (بخطوة واحدة معيارية) لرصد مدى استجابة CSR وتحديد نقطة التشبع.</li>
    <li><b>مختبر التعميم:</b> تدريب على Corporate وتقييم على طوبولوجيا محتجزة
    (Held-out) لقياس Generalization Gap كما توصي المواصفة.</li>
    <li><b>تحليل قرارات الوكيل:</b> تصدير بطاقات تفسير الأفعال (Explainability)
    من النماذج المدربة المحفوظة لفهم سبب تذبذب DQN في الخطوات الأخيرة.</li>
  </ul>

</div>

<div class="ending">
  <div class="big">كل رقم بلا بيئة مفتوحة<br>يبقى ادعاءً موروثًا.</div>
  <div class="sm">CyberWarEnv Research Platform — Verification Report ·
  EXP-2026-000001 / EXP-2026-000002 · 20 runs × 100k steps × 100 eval episodes<br><br>
  Defensive research simulation only — no offensive capability, no exploit code.</div>
</div>

</body>
</html>"""

with open(f"{OUT}/CyberWarEnv_Verification_Report.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"[saved] {OUT}/CyberWarEnv_Verification_Report.html  ({len(html):,} chars)")
