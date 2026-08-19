"""
Gunicorn sozlamalari — production uchun.

Ishga tushirish:
    gunicorn config.wsgi:application -c gunicorn.conf.py
"""

import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# Django I/O ga bog'liq (baza, Redis, tashqi API) — CPU emas. Shuning uchun
# `gthread`: har bir worker bir nechta so'rovni parallel kutib turadi va
# 10 000+ foydalanuvchida jarayonlar soni portlab ketmaydi.
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", 4))
worker_connections = 1000

# Bitta so'rov cheksiz osilib qolmasin (nginx timeout'idan kichikroq bo'lsin).
timeout = 60
graceful_timeout = 30
keepalive = 5

# Xotira sizib ketishining oldini olish: har N so'rovdan keyin worker
# qayta tug'iladi. `jitter` — hamma worker bir vaqtda qayta ishga
# tushib, xizmatni cho'ktirib qo'ymasligi uchun.
max_requests = 1000
max_requests_jitter = 100

# Fayl tizimiga emas, xotiraga yozish — konteynerlarda tezroq.
worker_tmp_dir = "/dev/shm"

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" %(D)sus req=%({X-Request-ID}o)s'

preload_app = True
