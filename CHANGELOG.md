# 📋 CHANGELOG — Student 360

## v1.0-pilot (نسخه پایلوت یکپارچه)

### فاز 1 — PMV (تکمیل عملی)
- Event Tracking خودکار (middleware بک‌اند + tracker فرانت + throttle + audit endpoint)
- Data Marts: ۵ SQL view (GPA وزنی، تقاضا، رویداد روزانه/تجموعی، ترم) + refresh خودکار
- لایه AI: LLM سازگار با OpenAI (AvalAI) + RAG فارسی TF-IDF + Prompt Guardrails + fallback قطعی
- داشبورد تحلیل ادمین: recharts + تقویم شمسی heatmap + پیش‌بینی تقاضا (RandomForest)
- اتصال GPA وزنی مارت به پروفایل هوشمند (مسیر بک‌اند + فرانت)

### فاز 2 — شخصی‌سازی و تحلیل
- Behavioral Insights: شاخص تعامل ۵ مؤلفه‌ای (Tehran TZ) + رتبه‌بندی کارشناس
- ریسک تحصیلی: مدل قاعده‌محور ۵ عاملی + **ML RandomForest ensemble** (train/predict API)
- مداخله‌های حمایتی: چرخه کامل اسکن(idempotent+cooldown) → بررسی کارشناس → شفافیت دانشجو
- مسیر تحصیلی شخصی‌سازی‌شده: سقف واحد آیین‌نامه‌ای × تعدیل ریسک + برنامه‌ریز پیش‌نیاز-آگاه
- کوییز تطبیقی LLM: سه سطح + تولید از محتوای درس + تصحیح سرور + fallback قطعی
- پروفایل شغلی: استخراج مهارت (keyword + LLM cache) + آمادگی ۵ مسیر + توصیه دروس
- کیفیت پاسخ‌ها: NLP بازخورد (مضمون‌های نارضایتی + توصیه‌های محصولی)
- میز کار کارشناس + ورود سه‌کاناله (OTP/SSO/کارشناس)

### فاز 3 — اکوسیستم راهبردی (آغاز)
- Digital Twin: شبیه‌سازی «چه می‌شود اگر» بدون نوشتن در DB + توضیح‌گر LLM
- Knowledge Graph: networkx (پیش‌نیاز بازگشتی، مهارت، شرط‌ها، fuzzy + نرمال‌سازی کاراکترهای نامرئی)
- Graph-aware RAG: استناد LLM به گراف دروس در پاسخ‌های آیین‌نامه‌ای
- Visualization: react-flow subgraph زنده در پنل کارشناس

### زیرساخت و کیفیت
- ۲۱ تست رگرسیون pytest (همه سبز)
- ریپوی تمیز: بدون node_modules/db/.env؛ push خودکار با گیت هوشمند
- رفع ۱۶+ باگ (شامل circular import تاریخی، تقویم جلالی معکوس، کاراکترهای نامرئی فارسی ZWNJ/LRM، cooldown مداخله، fresh-install ریسک)

### افزودنی پس از v1.0-pilot — ادغام فیچر نظرسنجی دروس (از ریپوی همکار)
- بک‌اند: ۴ روتر votes/vote-polls/proposals/ratings با prefix /api (۸ endpoint)
- حل تعارض‌های ORM: duplicate Student، FK به stu_students، back_populates یک‌طرفه، route ordering
- هاب دانشجویی: ۳ تب (رأی/پیشنهاد/امتیاز) با انتخابگر جستجودار دروس + ثبت با student_id resolve
- آمار زنده: stats-all (👍/📌 per درس با عنوان) + all-list پیشنهادها با نام دانشجو
- کارشناس: صفحه نظرسنجی (آمار + پیشنهادها + مدیریت) — دانشجو: هاب ۳ تبی
- زیرساخت: proxy /api در Vite + ۲۱ تست رگرسیون (پایدار در تمام ادغام)
