# CampSage — California campsite finder. Two roles share this one image:
#   • web     → serves the phone status page + map  (python campsage_web.py)
#   • scanner → runs the scan on a schedule         (python scheduler.py)
# See docker-compose.yml.
FROM python:3.12-slim

# Flask is the only third-party dep; the scanner itself is stdlib-only.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

WORKDIR /app
COPY . /app

# Scan output / caches live on a mounted volume here (see config.DATA_DIR).
ENV CAMPSAGE_DATA_DIR=/data \
    CAMPSAGE_WEB_PORT=5001 \
    PYTHONUNBUFFERED=1
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 5001

# Default to the web server; the scanner service overrides `command:` in compose.
CMD ["python", "campsage_web.py"]
