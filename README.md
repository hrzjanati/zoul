# زول (Zoul)

ایجنت شخصی شبیه **Muse متا**: با کامپیوتر خودش کار می‌کند، بعد از بستن اپ هم ادامه می‌دهد، و قبل از هر کار برگشت‌ناپذیر (ارسال ایمیل و پیام، خرید) از من تأیید می‌گیرد.

- **پنل:** جنگو (پایتون)، با همان ساختار «خانواده من».
- **موتور ایجنت:** [OpenMuse](https://github.com/OpenMuseAgent/OpenMuse) 0.6.0 (MIT).
- **UI:** UI موبایل OpenMuse، فارسی‌شده و دوزبانه (فارسی پیش‌فرض و English) با راست‌به‌چپ. سورس در `engine/web/`.
- **مدل:** فعلاً DeepSeek. بعداً انتخاب بین Claude، Gemini، GPT و DeepSeek با کلید خود کاربر (BYOK).
- **اجرا:** فقط Docker. میزبانی روی همروش (Darkube) با ۱ هسته و ۲ گیگ رم.

## اجرای لوکال

```bash
cp .env.example .env        # DEEPSEEK_API_KEY را پر کن
docker compose up --build
```

- اپ ایجنت (UI خود OpenMuse): http://localhost:8000/?token=<OPENMUSE_SERVER_TOKEN>
- صفحهٔ وضعیت زول: http://localhost:8000/zoul/
- ادمین: http://localhost:8000/admin/

روی همروش: `https://zoul.darkube.ir/?token=...`

## ساختار

```
zoul/
├── config/             پروژهٔ جنگو (settings، urls، wsgi)
├── home/               صفحهٔ اصلی و بررسی سلامت
├── engine/             پل به موتور OpenMuse
│   ├── services/openmuse_client.py   تنها درگاه به API موتور
│   ├── openmuse/config.toml          تنظیمات موتور (مدل، Sentinel، کانکتورها)
│   └── web/                          سورس UI دوزبانه (React + Vite)
├── deploy/nginx.conf   دروازهٔ پورت 8000 (UI موتور + جنگو)
├── docs/               قوانین، معرفی پروژه و سند هر فیچر
├── Dockerfile، docker-compose.yml، docker-entrypoint.sh
└── requirements.txt، .env.example، version.txt
```

## مستندات

- [docs/RULES.md](docs/RULES.md): قوانین کار روی پروژه
- [docs/PROJECT.md](docs/PROJECT.md): هدف، معماری، تصمیم‌ها و مراحل
- [docs/features/](docs/features/README.md): برای هر فیچر یک فایل
