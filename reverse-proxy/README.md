# Apache reverse proxy — Installation

## 1. Enable the required Apache modules

```bash
sudo a2enmod proxy proxy_http ssl headers rewrite
```

## 2. Prepare the directory for Let's Encrypt renewal (webroot mode)

```bash
sudo mkdir -p /var/www/certbot
```

## 3. Copy and adapt the configuration

Copy `apache-transcription.conf` to `/etc/apache2/sites-available/` and
adapt:
- `ServerName` (the real domain name)
- SSL certificate paths
- upstream port (`127.0.0.1:8080` by default) if `FRONTEND_HOST_PORT` was
  changed in the project's `.env`
- `LimitRequestBody`: must be **greater than or equal to** the file size
  limit configured in the application's admin panel (Upload limits → Max
  size in MB). The Apache value is an upstream safeguard; the application
  limit is what produces the clear error message for the user.

  MB → bytes conversion: `size_mb * 1024 * 1024`
  (e.g. 300 MB = 314572800 bytes, the value already used in the example)

## 4. Generate the Let's Encrypt certificate

Before the first HTTPS launch, enable only the `:80` VirtualHost (without
the redirect to HTTPS) to let certbot validate the domain, or directly use
certbot's Apache plugin:

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d transcription.example.com
# or, simpler if Apache is already configured for the domain:
sudo certbot --apache -d transcription.example.com
```

Automatic renewal is usually already scheduled by the `certbot` package
(systemd timer or cron job). Check with:

```bash
sudo certbot renew --dry-run
```

## 5. Enable the site and reload Apache

```bash
sudo a2ensite apache-transcription.conf
sudo apache2ctl configtest   # validates the syntax before reloading
sudo systemctl reload apache2
```

## 6. Start the application with the frontend port correctly exposed

The project's `docker-compose.yml` already exposes the `frontend` container
on `127.0.0.1:${FRONTEND_HOST_PORT:-8080}` (so it is only reachable from
the host machine, not from the outside — only Apache should be able to
reach it). No change is needed if you keep the default port (8080);
otherwise, adjust `FRONTEND_HOST_PORT` in `.env` **and** the `ProxyPass`
directive in `apache-transcription.conf` accordingly.

```bash
docker-compose up -d
```

## 7. Verification

```bash
curl -I https://transcription.example.com
curl -I https://transcription.example.com/api/health
```

The first command must return the application's home page (React UI), the
second `{"status": "ok"}` through the frontend's internal `/api` proxy to
the backend.
