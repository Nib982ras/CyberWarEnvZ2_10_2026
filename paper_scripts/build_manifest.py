#!/usr/bin/env python3
"""Build the bilingual file manifest (AR+EN) into download/00_FILE_MANIFEST.md."""
import os
import datetime

DL = "/home/z/my-project/download"
ROOT = "/home/z/my-project"

def size_h(p):
    if not os.path.exists(p):
        return "MISSING / مفقود"
    total = 0
    if os.path.isdir(p):
        for dp, _, fns in os.walk(p):
            for f in fns:
                total += os.path.getsize(os.path.join(dp, f))
    else:
        total = os.path.getsize(p)
    return f"{total/1024/1024:.1f} MB" if total > 1024*1024 else f"{total/1024:.0f} KB"

ITEMS = [
    ("CyberWarEnv_Q1_Paper/", "الورقة البحثية النهائية (IEEE, 8 صفحات) + المصدر الوحدوي + المدمج + مراجع + أشكال",
     "Final paper (IEEE, 8 pp) + modular LaTeX source + flattened tex + bib + figures"),
    ("CyberWarEnv_Q1_Paper_Source.zip", "حزمة مصدر الورقة كاملة مضغوطة", "Full paper source package (zipped)"),
    ("CyberWarEnv_elsarticle/", "حزمة التقديم لإلسفير: مخطوطة elsarticle بأرقام الأسطر + PDF + Highlights + خطاب التغطية (PDF/tex/txt) + README",
     "Elsevier submission package: elsarticle manuscript (line-numbered) + PDF + Highlights + cover letter (PDF/tex/txt) + README"),
    ("CyberWarEnv_elsarticle_Submission.zip", "حزمة التقديم كاملة في أرشيف واحد", "Whole submission package in one archive"),
    ("CyberWarEnv_Response_and_Change_Log.docx", "رفيق الرد وسجل التغييرات: جدول التحسينات + رسالة الاستفسار + الردود الجاهزة + ملاحظة عربية",
     "Rebuttal & change-log companion: improvements table + inquiry email + prepared responses + Arabic note"),
    ("CyberWarEnv_Final_Report_EN.pdf", "التقرير النهائي — النسخة الإنجليزية", "Final report — English edition"),
    ("CyberWarEnv_Final_Report_EN.html", "مصدر التقرير الإنجليزي (HTML قابل للتعديل)", "English report HTML source (editable)"),
    ("CyberWarEnv_Final_Report_AR.pdf", "التقرير النهائي — النسخة العربية (RTL)", "Final report — Arabic edition (RTL)"),
    ("CyberWarEnv_Final_Report_AR.html", "مصدر التقرير العربي (HTML قابل للتعديل)", "Arabic report HTML source (editable)"),
    ("CyberWarEnv_Verification_Report.pdf", "تقرير التحقق العلمي (عربي، 9 صفحات)", "Verification report (Arabic, 9 pp)"),
    ("CyberWarEnv_Verification_Report_EN.pdf", "تقرير التحقق العلمي (إنجليزي، 10 صفحات)", "Verification report (English, 10 pp)"),
    ("CyberWarEnv_Verification_Report.html", "مصدر تقرير التحقق العربي", "Arabic verification report HTML source"),
    ("CyberWarEnv_Verification_Report_EN.html", "مصدر تقرير التحقق الإنجليزي", "English verification report HTML source"),
    ("CyberWarEnv_Reproducible_Package.zip", "حزمة إعادة الإنتاج: بيئة + سكربتات + تشغيلات + نماذج", "Reproducible package: env + scripts + runs + models"),
    ("CyberWarEnv_Dataset_Registry.zip", "سجل البيانات الكامل cyberwarenv_runs/ (8 تجارب × 10 تشغيلات)", "Complete dataset registry cyberwarenv_runs/ (8 experiments x 10 runs)"),
    ("CyberWarEnv_Platform_Master_Prompt.md", "مواصفة إعادة بناء المنصة كاملة", "Full platform rebuild specification"),
    ("README.md", "دليل مجلد التنزيل", "Download folder guide"),
    ("00_FILE_MANIFEST.md", "هذا البيان (عربي + إنجليزي)", "This manifest (Arabic + English)"),
    ("figures/", "الأشكال النشرية الثلاثة (PNG)", "Three publication figures (PNG)"),
]

now = datetime.date.today().isoformat()
lines = []
lines.append("# بيان الملفات الكامل — CyberWarEnv / Complete File Manifest\n")
lines.append(f"آخر تحديث / Last updated: {now}\n")
lines.append(f"المجلد الرئيسي / Root folder: `{DL}/`\n")
lines.append("\n## الجرد / Inventory\n")
lines.append("| المسار / Path | الحجم / Size | الوصف (عربي) | Description (EN) |")
lines.append("|---|---|---|---|")
for path, ar, en in ITEMS:
    lines.append(f"| `{path}` | {size_h(os.path.join(DL, path))} | {ar} | {en} |")

lines.append("\n### السجل الخام / Raw registry\n")
lines.append("- `cyberwarenv_runs/` — في جذر المشروع `/home/z/my-project/` (خارج مجلد التنزيل)، ويحوي 8 تجارب × 10 تشغيلات = 80 مجلد تشغيلة، كل تشغيلة بـ config.json وresults.json وmanifest.json (SHA-256) وmodel.zip.")
lines.append("- The canonical raw registry lives at project root `/home/z/my-project/cyberwarenv_runs/` (outside download/): 8 experiments x 10 runs = 80 run folders, each with config.json, results.json, manifest.json (SHA-256), and model.zip.")
lines.append("- نسخة مضغوطة من السجل متاحة هنا باسم `CyberWarEnv_Dataset_Registry.zip`. / A zipped copy ships here as `CyberWarEnv_Dataset_Registry.zip`.\n")

lines.append("\n## ملاحظات / Notes\n")
lines.append("1. كل الأرقام في كل المستندات محسوبة من `paper_analysis.json` داخل السجل — لا قيم مفترضة. / Every number in every document is computed from `paper_analysis.json` in the registry — no assumed values.")
lines.append("2. قبل الإرسال إلى مجلة إلسفير راجع `CyberWarEnv_elsarticle/README_SUBMISSION.md` (سطرا المجلة + إقرارات الذكاء الاصطناعي). / Before submitting to an Elsevier journal review `CyberWarEnv_elsarticle/README_SUBMISSION.md` (journal line + AI declarations).")
lines.append("3. قرار التقديم: إن كانت مجلة الرفض هي Computers & Security فبدّل الهدف إلى Journal of Information Security and Applications — التفصيل في التقرير النهائي القسم 06 ورسالة الاستفسار الجاهزة في مستند الرفيق. / Submission decision: if the rejecting journal was Computers & Security, retarget JISA — details in Final Report Section 06 and the ready-made inquiry email in the companion docx.")

out = os.path.join(DL, "00_FILE_MANIFEST.md")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("WROTE", out)
