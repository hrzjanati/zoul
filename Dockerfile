# ======================================================================
#  ایمیج زول: پنل جنگو + موتور OpenMuse در یک ایمیج
# ----------------------------------------------------------------------
#  روی همروش یک کانتینر بالا می‌آید و docker-compose اجرا نمی‌شود؛ پس
#  entrypoint هر دو پروسه را راه می‌اندازد (مثل حلقهٔ یادآوری «خانواده من»).
#  لوکال، docker-compose هر کدام را سرویس جدا اجرا می‌کند.
# ======================================================================
# میرور داخلی همروش، چون Docker Hub از داخل ایران قابل اتکا نیست.
# پایتون ۳٫۱۳: بالاترین نسخه‌ای که OpenMuse 0.5.0 پشتیبانی می‌کند.
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
RUN apt-get update && apt-get install -y --no-install-recommends \
    bubblewrap \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .
# -i به مخزن اصلی، مثل «خانواده من»، تا میرور با 404 بیلد را نشکند.
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.org/simple/

COPY . .

COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# collectstatic و check در زمان بیلد؛ کلید دورریختنی فقط برای همین مرحله.
RUN DEBUG=False SECRET_KEY="build-time-throwaway-key-not-used-at-runtime" \
    python manage.py collectstatic --noinput --clear \
 && DEBUG=False SECRET_KEY="build-time-throwaway-key-not-used-at-runtime" \
    python manage.py check

# پوشهٔ داده (دیتابیس‌های OpenMuse، Vault، فضای کار ایجنت). روی همروش
# باید دیسک دائمی به /data وصل شود، وگرنه با هر ری‌استارت حافظه پاک می‌شود.
VOLUME ["/data"]

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
