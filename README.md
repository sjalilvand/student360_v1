# 🎓 دانشجو ۳۶۰ — Student 360

سامانه یکپارچه خدمات دانشجویی هوشمند — پیاده‌سازی «نقشه راه دانشجو ۳۶۰» در سه فاز
(PMV، شخصی‌سازی و تحلیل، اکوسیستم راهبردی) با AI واقعی (LLM + RAG + Guardrails)،
پیش‌بینی ML، گراف دانش دروس و Digital Twin.

## 🚀 اجرا

- بک‌اند (پورت 8000): `cd backend` → ساخت venv → `pip install -r requirements.txt` →
  `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- فرانت‌اند (پورت 5173): `cd frontend` → `npm install` → `npm run dev`
- تنظیمات: `backend/.env` را از الگوی `backend/.env.example` بسازید (کلید LLM).
- دیتابیس SQLite و داده پایلوت در اولین اجرا خودکار ساخته می‌شوند.

## 🧭 ورود پایلوت

| نقش | شناسه |
|---|---|
| دانشجو (OTP) | شماره 402101001 — کد در پاسخ API |
| دانشجو (SSO) | a.mohammadi |
| کارشناس آموزش | staff-admin / admin123 |

## ✨ پورتال دانشجو (۱۵ ماژول)

- پروفایل هوشمند — GPA وزنی از Data Mart
- بینش‌های رفتاری — شاخص تعامل ۵ مؤلفه‌ای + پیشنهادهای شخصی
- مسیر تحصیلی شخصی‌سازی‌شده — ریسک-آگاه با احترام به پیش‌نیازها
- دستیار آیین‌نامه‌ای — LLM+RAG با ارجاع منبع و Guardrails
- راهنمای فرایندها، دستیار انتخاب واحد، بررسی فارغ‌التحصیلی
- تقویم و یادآوری، هشدارها، کوییز هوشمند
- کوییز تطبیقی LLM — سه سطح، تطبیق خودکار، تصحیح سمت سرور
- استاد هوشمند — LLM با منابع درس
- پروفایل شغلی — استخراج مهارت (keyword + LLM cache) + آمادگی ۵ مسیر
- Digital Twin — شبیه‌سازی «چه می‌شود اگر» + توضیح‌گر LLM + fallback گراف
- دستیار هوشمند یکپارچه (RAG)

## ✨ پنل کارشناس (۸ ماژول)

- میز کار (آمار کلی + آخرین ورودها) • دانشجویان (GPA وزنی از مارت)
- تعامل دانشجویان (رتبه‌بندی) • هشدار ریسک تحصیلی (قواعد + **ML RandomForest ensemble**)
- مداخله‌های حمایتی (چرخه کامل: اسکن idempotent با cooldown ← بررسی ← شفافیت دانشجو)
- کیفیت پاسخ‌ها (NLP بازخورد با LLM: مضمون‌ها + توصیه‌های محصولی)
- گراف دروس (کاوش fuzzy، مسیر یادگیری، Visualization با react-flow)

## 📊 داشبورد تحلیل (ادمین)

۵ مارت SQL • تقویم شمسی رویدادها (heatmap) • پیش‌بینی تقاضا (RandomForest) •
تقاضا vs ثبت‌نام • GPA وزنی دانشجویان

## 🏗 معماری

- backend/app/api — ۲۰+ روتر REST
- backend/app/services — ۲۵+ سرویس (risk, risk_ml, behavioral, twin, RAG, graph, skills, feedback-NLP, ...)
- backend/app/models — SQLAlchemy (Student360 + event log + interventions + skills cache)
- backend/app/core — database, event-tracking middleware, guardrails, AI integration
- frontend/src — React 18 + Vite + recharts + reactflow (پورتال role-aware)

زیرساخت کلیدی:
- Event Tracking خودکار (middleware + فرانت) → stu_event_logs
- Data Marts: ۵ SQL view (GPA وزنی، تقاضا، رویداد روزانه/تجموعی، ترم)
- RAG فارسی: TF-IDF روی Regulation/Guide/Curriculum + Prompt Guardrails
- LLM: هر endpoint سازگار با OpenAI (AvalAI/…) + fallback قطعی
- Knowledge Graph: networkx (پیش‌نیاز + مهارت + شرط‌ها، fuzzy و ZWNJ-safe)
- ML: RandomForest (تقاضا + ریسک با برچسب distilled و ensemble با قواعد)

## 🧪 تست‌ها

cd backend
.venv\Scripts\python -m pytest tests/test_phase2_services.py -o addopts="" -q

۲۰ رگرسیون: جلالی، guardrails، مارت/GPA وزنی، ریسک، cooldown مداخله، کوییز تطبیقی،
مسیر تحصیلی، مهارت شغلی، NLP بازخورد، Digital Twin، چرخه ML، Knowledge Graph.

## 🔐 امنیت

- کلید LLM فقط در backend/.env (gitignored) — الگو: backend/.env.example
- دیتابیس‌ها و ml_models/ گیت‌ایگنور شده
- node_modules از ریپو حذف (deps با npm install)
- لاگ ممیزی stu_audit_logs + همه پاسخ‌های AI با برچسب موتور و disclaimer

## 🗺 وضعیت نقشه راه

فاز ۱ (PMV) ≈ ۹۷٪ | فاز ۲ (شخصی‌سازی/تحلیل) ≈ ۶۸٪ | فاز ۳ (راهبردی) ≈ ۶۰٪ آغازشده
(Digital Twin، گراف دانش، ML ریسک). مستند کامل ۱۷ دسته: سند نقشه راه پروژه.
