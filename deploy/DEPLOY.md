# Feasto — serverga chiqarish

Ubuntu 22.04 / 24.04 uchun. Boshidan oxirigacha ~40 daqiqa.

Talablar: 2 vCPU / 4 GB RAM (boshlash uchun), `feasto.uz` domenining
A-yozuvi server IP'siga yo'naltirilgan bo'lsin.

---

## 1. Tizim paketlari

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-dev build-essential \
    postgresql postgresql-contrib redis-server \
    nginx certbot python3-certbot-nginx git curl
```

## 2. Foydalanuvchi va papkalar

Ilova **o'z foydalanuvchisi** ostida ishlaydi — `root` ostida emas.
Sayt buzilsa ham, hujumchi faqat shu foydalanuvchi huquqini oladi.

```bash
sudo adduser --system --group --home /srv/feasto feasto
sudo mkdir -p /srv/feasto/{media,logs,run,staticfiles}
sudo mkdir -p /srv/backups/feasto /var/www/certbot
sudo chown -R feasto:www-data /srv/feasto
```

## 3. Kod va virtual muhit

```bash
sudo -u feasto git clone https://github.com/akobirmarupov/wenzu.git /srv/feasto/src
sudo -u feasto cp -r /srv/feasto/src/. /srv/feasto/
sudo -u feasto rm -rf /srv/feasto/src

cd /srv/feasto
sudo -u feasto python3 -m venv venv
sudo -u feasto venv/bin/pip install --upgrade pip
sudo -u feasto venv/bin/pip install -r requirements.txt
sudo -u feasto venv/bin/pip install gunicorn
```

## 4. Ma'lumotlar bazasi

```bash
sudo -u postgres psql <<'SQL'
CREATE USER feasto_user WITH PASSWORD 'BU_YERGA_KUCHLI_PAROL';
CREATE DATABASE feasto_db OWNER feasto_user;
ALTER ROLE feasto_user SET client_encoding TO 'utf8';
ALTER ROLE feasto_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE feasto_user SET timezone TO 'Asia/Tashkent';
SQL
```

## 5. `.env`

```bash
sudo -u feasto cp /srv/feasto/.env.example /srv/feasto/.env
sudo -u feasto nano /srv/feasto/.env
sudo chmod 600 /srv/feasto/.env
```

To'ldirilishi **shart** bo'lganlar:

| Kalit | Qiymat |
|---|---|
| `SECRET_KEY` | yangi tasodifiy kalit (buyrug'i faylning o'zida yozilgan) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `feasto.uz,www.feasto.uz` |
| `DB_PASSWORD` | 4-bosqichda qo'ygan parol |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | 9-bosqichga qarang |

> `SECRET_KEY` ni ishlab chiqishdagi bilan bir xil qoldirmang. U
> sessiya va tokenlarni imzolaydi: bir xil bo'lsa, lokal kalitni
> bilgan odam production sessiyasini soxtalashtira oladi.

## 6. Migratsiya va statik fayllar

```bash
cd /srv/feasto
sudo -u feasto venv/bin/python manage.py migrate
sudo -u feasto venv/bin/python manage.py collectstatic --noinput
sudo -u feasto venv/bin/python manage.py seed_platform   # sozlamalar + tariflar
sudo -u feasto venv/bin/python manage.py createsuperuser
```

## 7. systemd xizmatlari

```bash
sudo cp /srv/feasto/deploy/feasto.socket          /etc/systemd/system/
sudo cp /srv/feasto/deploy/feasto.service         /etc/systemd/system/
sudo cp /srv/feasto/deploy/feasto-worker.service  /etc/systemd/system/
sudo cp /srv/feasto/deploy/feasto-beat.service    /etc/systemd/system/
sudo cp /srv/feasto/deploy/feasto-backup.service  /etc/systemd/system/
sudo cp /srv/feasto/deploy/feasto-backup.timer    /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now feasto.socket feasto.service
sudo systemctl enable --now feasto-worker feasto-beat
sudo systemctl enable --now feasto-backup.timer

sudo systemctl status feasto --no-pager
```

> **Beat faqat bitta nusxada.** Ikkita server qo'shsangiz,
> `feasto-beat` ulardan faqat BIRIDA yoqilsin — aks holda har kungi
> vazifalar ikki marta bajariladi.

## 8. nginx va HTTPS

```bash
sudo cp /srv/feasto/deploy/feasto_proxy.conf /etc/nginx/feasto_proxy.conf
sudo cp /srv/feasto/deploy/nginx.conf /etc/nginx/sites-available/feasto
sudo ln -sf /etc/nginx/sites-available/feasto /etc/nginx/sites-enabled/feasto
sudo rm -f /etc/nginx/sites-enabled/default

# Sertifikat olish (nginx sozlamasi hali HTTPS ga tayanadi, shuning
# uchun certbot'ni --nginx bilan ishga tushiramiz — u o'zi vaqtincha
# moslab oladi).
sudo certbot --nginx -d feasto.uz -d www.feasto.uz

sudo nginx -t && sudo systemctl reload nginx
```

Certbot yangilanishni o'zi jadvalga qo'yadi. Tekshirish:

```bash
sudo certbot renew --dry-run
```

## 9. Google bilan kirish

`console.cloud.google.com` → APIs & Services → Credentials → OAuth client:

**Authorized JavaScript origins**
```
https://feasto.uz
```

**Authorized redirect URIs**
```
https://feasto.uz/api/auth/google/callback/
```

Chiqqan `Client ID` va `Client secret` ni `.env` ga yozing va
xizmatni qayta yuklang:

```bash
sudo systemctl restart feasto
```

## 10. Ishga tushgandan keyin tekshirish

```bash
curl -I https://feasto.uz                      # 200 kutiladi
curl -I http://feasto.uz                       # 301 → https
curl -I https://feasto.uz/static/css/base/_tokens.css   # 200
```

Brauzerda qo'lda:

- [ ] bosh sahifa ochiladi, taomlar tasmasi aylanadi
- [ ] Google bilan kirish ishlaydi
- [ ] profil ochiladi, rasm yuklanadi va **ko'rinadi** (`/media/` tekshiruvi)
- [ ] restoran tanlab bron qilinadi
- [ ] adminka: `https://feasto.uz/admin/`
- [ ] telefonda: pastki menyu, til almashtirgich, sozlamalar oynasi

## 11. Yangilash tartibi

```bash
cd /srv/feasto
sudo -u feasto git pull
sudo -u feasto venv/bin/pip install -r requirements.txt
sudo -u feasto venv/bin/python manage.py migrate
sudo -u feasto venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart feasto feasto-worker feasto-beat
```

## 12. Nosozlik bo'lsa

```bash
sudo journalctl -u feasto -n 100 --no-pager        # ilova
sudo journalctl -u feasto-worker -n 50 --no-pager  # fon vazifalari
sudo tail -n 100 /var/log/nginx/feasto.error.log   # nginx
sudo tail -n 100 /srv/feasto/logs/feasto.log       # Django
```

**Tez-tez uchraydigan uchta xato:**

| Belgi | Sabab | Yechim |
|---|---|---|
| `502 Bad Gateway` | gunicorn ko'tarilmagan | `journalctl -u feasto` — odatda `.env` da xato |
| Cheksiz yo'naltirish | `X-Forwarded-Proto` yetmayapti | `/etc/nginx/feasto_proxy.conf` ulanganini tekshiring |
| Rasmlar 404 | `/media/` nginx'da yo'q yoki huquq yetmayapti | `ls -la /srv/feasto/media`, egasi `feasto:www-data` bo'lsin |

## 13. Zaxira

Har kuni 03:30 da baza va rasmlar `/srv/backups/feasto` ga saqlanadi,
14 kunlik nusxa turadi.

```bash
sudo systemctl list-timers feasto-backup    # jadval
sudo /srv/feasto/deploy/backup.sh           # qo'lda sinash
```

> **Zaxira boshqa joyda ham turishi kerak.** Server diski yonsa,
> undagi zaxira ham yonadi. `deploy/backup.sh` oxiridagi `rclone`
> qatorini o'z omboringizga moslab oching.

Tiklash:

```bash
PGPASSWORD=... pg_restore --host=127.0.0.1 --username=feasto_user \
    --dbname=feasto_db --clean --if-exists /srv/backups/feasto/db_YYYY-MM-DD_HHMM.dump
tar -xzf /srv/backups/feasto/media_YYYY-MM-DD_HHMM.tar.gz -C /srv/feasto
```
