# دليل النشر على GitHub / Publish-to-GitHub Guide

ثنائي اللغة: اتبع القسم العربي أو الإنجليزي — الخطوات نفسها.
Bilingual: follow either section — the steps are identical.

---

## العربية

### لماذا هذه الخطوة ضرورية؟
ورقتك وخطاب التغطية يذكران أن "كل المواد الداعمة متاحة للتحقق المستقل" — لكن حتى
الآن لا يوجد أي مستودع عام. هذه الخطوة تجعل العبارة صادقة قبل التقديم إلى
Computers & Security.

### الخطوات (10 دقائق)

1. **أنشئ حساباً** على github.com إن لم يكن لديك (اسم المستخدم سيظهر في الرابط).

2. **أنشئ مستودعاً جديداً فارغاً**: اضغط `+` أعلى اليمين → `New repository`
   → الاسم: `CyberWarEnv` → اختر **Private** أولاً (يمكن جعله Public لاحقاً)
   → **لا** تختر README ولا License ولا .gitignore (لدينا نسخنا) → `Create repository`.

3. **من جهازك، بعد فك ضغط `CyberWarEnv_Code_Release.zip`**:
```bash
cd CyberWarEnv_Code_Release
git init -b main
git add .
git commit -m "CyberWarEnv v2.0.0 — code release: calibrated env + 80-run paper pipeline"
git remote add origin https://github.com/Nib982ras/CyberWarEnvZ2_10_2026.git
git branch -M main
git push -u origin main
git tag v2.0.0
git push origin v2.0.0
```
   (سيطلب توكن الوصول الشخصي — من GitHub: Settings → Developer settings →
   Personal access tokens → Generate، وامنحه صلاحية `repo`.)

4. **انشر بيانات التشغيلات (197 MB) على Zenodo** — لأن GitHub غير مناسب
   لهذا الحجم:
   - ادخل zenodo.org بحساب GitHub (أو أي حساب) → `New upload`
   - ارفع ملف `CyberWarEnv_Dataset_Registry.zip`
   - املأ: العنوان "CyberWarEnv Run Registry (80 runs)", النوع Dataset،
     المؤلف Nibras Raad، ووصفاً مختصراً
   - بعد النشر اضغط زر **Get DOI** — ستحصل على DOI دائم مثل `10.5281/zenodo.XXXXXXX`

5. **اربط DOI بالمستودع**: في إعدادات مستودع GitHub → About → اكتب DOI في
   حقل "Cite this repository" (Zenodo يرتبط تلقائياً إذا ربطت الحسابين من
   zenodo.org → GitHub section → Enable على مستودع CyberWarEnv).

6. **حدّث عبارة توفر البيانات في المخطوطة** (نهاية ملف
   `CyberWarEnv_elsarticle.tex`) بالرابط الحقيقي:
   ```
   The complete run registry (80 runs, model weights, SHA-256 manifests) is
   publicly available at https://github.com/Nib982ras/CyberWarEnvZ2_10_2026 (code) and
   https://doi.org/10.5281/zenodo.XXXXXXX (data).
   ```
   وأعِد ترجمة الـ PDF: `tectonic CyberWarEnv_elsarticle.tex`

7. **اجعل المستودع Public** قبل يوم التقديم (Settings → General → Danger Zone →
   Change visibility) — أو أبقه Private وأرسل رابط دعوة للمراجعين إذا أردت.

---

## English

### Why this step is required
The manuscript and cover letter state that "all supporting artifacts are
publicly released" — but no public repository exists yet. This step makes the
statement true before submitting to Computers & Security.

### Steps (10 minutes)

1. **Create a GitHub account** if you do not have one.

2. **Create a new empty repository**: `+` → `New repository` → name:
   `CyberWarEnv` → choose **Private** first (flip to Public later) →
   do **not** initialize with README/License/.gitignore → `Create repository`.

3. **From your machine, after unzipping `CyberWarEnv_Code_Release.zip`**:
```bash
cd CyberWarEnv_Code_Release
git init -b main
git add .
git commit -m "CyberWarEnv v2.0.0 — code release: calibrated env + 80-run paper pipeline"
git remote add origin https://github.com/Nib982ras/CyberWarEnvZ2_10_2026.git
git branch -M main
git push -u origin main
git tag v2.0.0
git push origin v2.0.0
```
   (Authentication uses a Personal Access Token: Settings → Developer settings
   → Personal access tokens → Generate with `repo` scope.)

4. **Publish the run registry (197 MB) on Zenodo** — git/GitHub is not
   suitable for this size:
   - Log in at zenodo.org → `New upload`
   - Upload `CyberWarEnv_Dataset_Registry.zip`
   - Title: "CyberWarEnv Run Registry (80 runs)", Type: Dataset,
     Author: Nibras Raad
   - After publishing click **Get DOI** — you receive a permanent DOI like
     `10.5281/zenodo.XXXXXXX`

5. **Link the DOI to the repository** (GitHub repo About → "Cite this
   repository"), or enable the Zenodo–GitHub integration for automatic DOI
   per release.

6. **Update the data-availability statement** in
   `CyberWarEnv_elsarticle.tex` with the real URLs (template above), then
   recompile: `tectonic CyberWarEnv_elsarticle.tex`.

7. **Make the repository Public** on submission day (Settings → General →
   Danger Zone → Change visibility), or keep it Private and invite reviewers.
