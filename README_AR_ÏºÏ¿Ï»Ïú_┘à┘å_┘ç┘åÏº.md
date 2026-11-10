# ابدأ من هنا — شرح مبسط

**هدفنا:** مشروع Data Engineer عملي للتقديم، مش تدريب Python نظري.

## تشغيل المشروع بسرعة

1. فك الضغط وافتح فولدر `EP_LiDAR_Data_Engineering` من **File > Open Folder** في VS Code.
2. افتح **Terminal > New Terminal**. لازم يكون الـ Terminal داخل الفولدر اللي فيه `requirements.txt`.
3. نفذ الخمس أوامر دول واحد واحد:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe src/generate_sample.py
.venv\Scripts\python.exe src/pipeline.py
.venv\Scripts\python.exe src/visualize.py
```

4. شوف النتائج في `data/processed/`، خصوصًا `quality_report.json` و`point_cloud_preview.png`.
5. اختبر المشروع:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## كل ملف بيعمل إيه؟

- `generate_sample.py`: بيولد بيانات **تجريبية صناعية** علشان نقدر نجرب بسرعة. دي مش بيانات مستشعر حقيقي.
- `pipeline.py`: بيقرأ البيانات، يشيل القيم الغلط والمكررة، يحسب النسب، ويحفظ النتائج في CSV وSQLite.
- `visualize.py`: بيرسم النقط في 3D علشان نشوف توزيعها.
- `tests/test_pipeline.py`: بيختبر إن التنظيف فعلاً بيشيل الأخطاء حسب القواعد اللي كتبناها.
- `dataset_manifest.json`: بصمة للبيانات علشان نعرف لو النسخة اتغيرت.

## مهم للمقابلة

قدر تشرح: ليه عملنا Data Validation؟ ليه بنفحص `NaN` و`Infinity`؟ ليه بنشيل التكرار **داخل نفس الـFrame** فقط؟ ليه بنقسم المشاهد مش النقط عشوائيًا؟ وليه البيانات الصناعية مش بديل لبيانات LiDAR حقيقية؟

مش لازم تحفظ كل السطور، لكن لازم تشغل المشروع عندك وتفهم النتايج قبل تحطه في CV.
