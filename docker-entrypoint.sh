#!/bin/sh
set -e

mkdir -p "${ZOUL_DATA_DIR:-/data/zoul}" "${OPENMUSE_DATA_DIR:-/data/openmuse}" "${OPENMUSE_WORKSPACE:-/data/workspace}"

# مهاجرت فقط در کانتینری که وب را بالا می‌آورد؛ سرویس‌های دیگر با
# SKIP_PREP=1 می‌آیند تا دو پروسه هم‌زمان روی یک دیتابیس مهاجرت نزنند.
if [ "${SKIP_PREP:-0}" != "1" ]; then
    echo "▶ Applying migrations..."
    python manage.py migrate --noinput
fi

# دستور صریح (مثل سرویس engine در docker-compose) همان اجرا می‌شود.
if [ "$#" -gt 0 ]; then
    echo "▶ Running: $*"
    exec "$@"
fi

# ----------------------------------------------------------------------
#  موتور OpenMuse — داخل همین کانتینر، پس‌زمینه
# ----------------------------------------------------------------------
#  روی همروش فقط همین یک کانتینر است. حلقهٔ while تا اگر موتور مرد،
#  بی‌صدا خاموش نماند: سایت بالا بود و فقط ایجنت کار نمی‌کرد — بدترین
#  نوع خرابی. با RUN_ENGINE=0 خاموش می‌شود (docker-compose لوکال).
if [ "${RUN_ENGINE:-1}" = "1" ]; then
    echo "▶ Starting OpenMuse engine in background..."
    (
        while true; do
            openmuse serve --config "$OPENMUSE_CONFIG" --no-qr || \
                echo "⚠ engine exited (code $?) — restarting in 15s"
            sleep 15
        done
    ) &
fi

# ۱ worker × ۴ ترد: سرور ۲ گیگی است و موتور هم رم می‌خواهد.
echo "▶ Starting Gunicorn..."
exec gunicorn \
    --env DJANGO_SETTINGS_MODULE=config.settings \
    --timeout=120 \
    --worker-class gthread \
    --workers ${GUNICORN_WORKERS:-1} \
    --threads 4 \
    --max-requests 1000 \
    --max-requests-jitter 200 \
    --bind 0.0.0.0:8000 \
    config.wsgi
