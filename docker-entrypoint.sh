#!/bin/sh
set -e

mkdir -p "${ZOUL_DATA_DIR:-/data/zoul}" "${OPENMUSE_DATA_DIR:-/data/openmuse}" "${OPENMUSE_WORKSPACE:-/data/workspace}"

# مهاجرت فقط در کانتینر اصلی؛ با SKIP_PREP=1 رد می‌شود.
if [ "${SKIP_PREP:-0}" != "1" ]; then
    echo "▶ Applying migrations..."
    python manage.py migrate --noinput
fi

# دستور صریح (مثلاً `docker compose run zoul python manage.py shell`) همان اجرا می‌شود.
if [ "$#" -gt 0 ]; then
    echo "▶ Running: $*"
    exec "$@"
fi

# ----------------------------------------------------------------------
#  سه پروسه در یک کانتینر (روی همروش فقط همین یک کانتینر است):
#    ۱. موتور OpenMuse  ← 127.0.0.1:8787  (پس‌زمینه)
#    ۲. gunicorn/جنگو    ← 127.0.0.1:8001  (پس‌زمینه)
#    ۳. nginx            ← 0.0.0.0:8000    (پروسهٔ اصلی)
#
#  هر کدام از دو پروسهٔ پس‌زمینه داخل حلقهٔ while است: اگر بمیرد، بعد از
#  چند ثانیه دوباره بالا می‌آید و در لاگ می‌نویسد — نه اینکه سایت ظاهراً
#  بالا باشد و یک بخشش بی‌صدا خاموش بماند.
# ----------------------------------------------------------------------
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
echo "▶ Starting Gunicorn in background..."
(
    while true; do
        gunicorn \
            --env DJANGO_SETTINGS_MODULE=config.settings \
            --timeout=120 \
            --worker-class gthread \
            --workers ${GUNICORN_WORKERS:-1} \
            --threads 4 \
            --max-requests 1000 \
            --max-requests-jitter 200 \
            --bind 127.0.0.1:8001 \
            config.wsgi || \
            echo "⚠ gunicorn exited (code $?) — restarting in 5s"
        sleep 5
    done
) &

echo "▶ Starting nginx on :8000..."
exec nginx -c /code/deploy/nginx.conf -g "daemon off;"
