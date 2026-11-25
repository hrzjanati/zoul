# ======================================================================
#  ایمیج زول: nginx + پنل جنگو + موتور OpenMuse در یک ایمیج
# ----------------------------------------------------------------------
#  روی همروش یک کانتینر بالا می‌آید و docker-compose اجرا نمی‌شود؛ پس
#  entrypoint هر سه پروسه را راه می‌اندازد (docs/features/gateway.md).
# ======================================================================

# ======================================================================
#  مرحلهٔ ۱ — UI دوزبانهٔ زول (فارسی/English) از engine/web
# ----------------------------------------------------------------------
#  UI داخل پکیج pip انگلیسیِ از پیش ساخته است؛ این مرحله نسخهٔ فارسی‌شده
#  را می‌سازد. تست‌ها (از جمله «هر متن UI ترجمهٔ فارسی دارد») قبل از build
#  اجرا می‌شوند تا متن بی‌ترجمه هیچ‌وقت به سرور نرسد.
#  مستند: docs/features/i18n.md
# ======================================================================
# میرور داخلی همروش، چون Docker Hub از داخل ایران قابل اتکا نیست.
FROM hub.hamdocker.ir/library/node:22-slim AS ui
WORKDIR /ui
COPY engine/web/package.json engine/web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY engine/web/ ./
RUN npm test && npm run build


# ======================================================================
#  مرحلهٔ ۲ — ایمیج نهایی
# ======================================================================
# پایتون ۳٫۱۳: بالاترین نسخه‌ای که OpenMuse 0.6.0 پشتیبانی می‌کند.
FROM hub.hamdocker.ir/library/python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Tehran \
    ZOUL_DATA_DIR=/data/zoul \
    OPENMUSE_DATA_DIR=/data/openmuse \
    OPENMUSE_WORKSPACE=/data/workspace \
    OPENMUSE_CONFIG=/code/engine/openmuse/config.toml

WORKDIR /code

# میرور داخلی pip برای سرعت.
RUN mkdir -p /root/.pip \
 && printf "[global]\nindex=https://pypi.iranserver.com/repository/pypi/pypi\nindex-url=https://pypi.iranserver.com/repository/pypi/simple\ntrusted-host=pypi.iranserver.com\n" \
 > /root/.pip/pip.conf

# bubblewrap: ایزوله‌کردن هر دستور shell/Python ایجنت (فقط لینوکس).
# اگر همروش اجازهٔ namespace ندهد، OpenMuse در حالت auto بی‌صدا بدون آن
# کار می‌کند — این را در مرحلهٔ ۲ چک می‌کنیم (docs/features/sentinel.md).
# tzdata: تا ساعت سیستم با TZ بالا یکی باشد.
# nginx: دروازهٔ پورت 8000 — UI و WebSocket موتور + جنگو (deploy/nginx.conf).
RUN apt-get update && apt-get install -y --no-install-recommends \
    bubblewrap \
    nginx \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .
# -i به مخزن اصلی، مثل «خانواده من»، تا میرور با 404 بیلد را نشکند.
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.org/simple/

COPY . .

# UI دوزبانه جای UI انگلیسیِ داخل پکیج openmuse می‌نشیند (همان پوشه‌ای که
# `openmuse serve` از آن سرو می‌کند).
COPY --from=ui /ui/dist /opt/zoul-ui
RUN STATIC="$(python -c 'import openmuse.server, pathlib; print(pathlib.Path(openmuse.server.__file__).parent / "static")')" \
 && rm -rf "${STATIC:?}" && cp -r /opt/zoul-ui "$STATIC" && rm -rf /opt/zoul-ui \
 && test -f "$STATIC/index.html"

COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# collectstatic و check در زمان بیلد؛ کلید دورریختنی فقط برای همین مرحله.
RUN DEBUG=False SECRET_KEY="build-time-throwaway-key-not-used-at-runtime" \
    python manage.py collectstatic --noinput --clear \
 && DEBUG=False SECRET_KEY="build-time-throwaway-key-not-used-at-runtime" \
    python manage.py check \
 && nginx -t -c /code/deploy/nginx.conf

# پوشهٔ داده (دیتابیس‌های OpenMuse، Vault، فضای کار ایجنت). روی همروش
# باید دیسک دائمی به /data وصل شود، وگرنه با هر ری‌استارت حافظه پاک می‌شود.
VOLUME ["/data"]

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
