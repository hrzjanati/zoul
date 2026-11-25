# موتور ایجنت: OpenMuse (اپ `engine`)

## این چیست؟
مغز زول. [OpenMuse](https://github.com/OpenMuseAgent/OpenMuse) 0.5.0 یک پروسهٔ همیشه‌روشن است (`openmuse serve`) که حلقهٔ ایجنت، ابزارها (فایل، shell، پایتون، جست‌وجو و خواندن وب، ایمیل، تقویم، مخاطبین، MCP)، حافظه، هدف‌ها، یادآوری‌ها، تریگرها، Vault و Sentinel را دارد. اپ `engine` پل جنگو به این موتور است.

## چه کار می‌کند؟
- موتور کنار جنگو اجرا می‌شود و روی `127.0.0.1:8787` گوش می‌دهد. از بیرون کانتینر مستقیم در دسترس نیست.
- اگر موتور بمیرد، entrypoint بعد از ۱۵ ثانیه دوباره راهش می‌اندازد و در لاگ می‌نویسد.
- جنگو فقط از راه `engine/services/openmuse_client.py` با موتور حرف می‌زند. فعلاً فقط `health()`.
- **`/engine/health/`**: جواب `{"engine": "up"|"down", "detail": ...}`، همیشه با کد ۲۰۰.
- داده‌های موتور در `/data/openmuse` است: `memory.db`، `goals.db`، `vault.enc`، `audit.jsonl` و `server_token`. فضای کار ایجنت `/data/workspace` است.

## کجای کد است؟
| فایل | نقش |
|---|---|
| `engine/services/openmuse_client.py` | **تنها** درگاه به API موتور. هیچ‌وقت استثنا بیرون نمی‌دهد |
| `engine/views.py`، `engine/urls.py` | `/engine/health/` |
| `engine/openmuse/config.toml` | تنظیمات موتور: مدل، Sentinel، sandbox، کانکتورها |
| `engine/openmuse/skills/` | Skillهای اختصاصی زول (فرمت `SKILL.md`). فعلاً خالی |
| `docker-entrypoint.sh` | اجرای موتور در پس‌زمینه با `RUN_ENGINE=1` |

## تنظیمات
| متغیر | توضیح |
|---|---|
| `DEEPSEEK_API_KEY` | کلید مدل |
| `OPENMUSE_LLM_MODEL` | نام مدل. خالی یعنی پیش‌فرض OpenMuse |
| `OPENMUSE_SERVER_TOKEN` | توکن API و وب‌اپ موتور. جنگو هم همین را می‌خواند |
| `OPENMUSE_URL` | آدرس موتور از دید جنگو. پیش‌فرض `http://127.0.0.1:8787` |
| `RUN_ENGINE` | `1` یعنی موتور داخل همین کانتینر (همروش). لوکال `0` |

فرمت `config.toml` مال خود OpenMuse است. `${VAR}` و `${VAR:-پیش‌فرض}` از محیط خوانده می‌شوند.

## تست
- `engine/tests.py`: موتور پایین، بالا و جواب غیر ۲۰۰. همهٔ درخواست‌ها mock شده‌اند.
- دستی: `docker compose up`، بعد باز کردن `http://localhost:8000/engine/health/` که باید `"up"` باشد.

## نکته‌ها و محدودیت‌ها
- OpenMuse مستقیم فقط endpointهای سازگار با OpenAI را می‌شناسد. Claude و Gemini از راه LiteLLM یا OpenRouter وصل می‌شوند (مرحلهٔ ۴).
- وب‌اپ موبایل خود OpenMuse فعلاً از بیرون باز نیست. نحوهٔ در دسترس قرار دادنش در مرحلهٔ ۲ تصمیم‌گیری می‌شود.
- مرورگر (Playwright و Chromium) خاموش است، به‌خاطر رم ۲ گیگ.
- DeepSeek عکس قبول نمی‌کند، برای همین `vision = "off"` است.
