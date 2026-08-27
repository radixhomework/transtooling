# Reverse proxy Apache — Installation

## 1. Activer les modules Apache nécessaires

```bash
sudo a2enmod proxy proxy_http ssl headers rewrite
```

## 2. Préparer le répertoire pour le renouvellement Let's Encrypt (mode webroot)

```bash
sudo mkdir -p /var/www/certbot
```

## 3. Copier et adapter la configuration

Copier `apache-transcription.conf` dans `/etc/apache2/sites-available/` et
adapter :
- `ServerName` (nom de domaine réel)
- chemins des certificats SSL
- port amont (`127.0.0.1:8080` par défaut) si `FRONTEND_HOST_PORT` a été
  modifié dans le `.env` du projet
- `LimitRequestBody` : doit être **supérieur ou égal** à la limite de
  taille de fichier configurée dans le panneau d'administration de
  l'application (Limites d'upload → Taille maximale en Mo). La valeur
  Apache est un garde-fou en amont ; c'est la limite applicative qui
  produit le message d'erreur clair pour l'utilisateur.

  Conversion Mo → octets : `taille_mo * 1024 * 1024`
  (ex: 300 Mo = 314572800 octets, valeur déjà utilisée dans l'exemple)

## 4. Générer le certificat Let's Encrypt

Avant le premier lancement HTTPS, activer uniquement le VirtualHost `:80`
(sans réécriture vers HTTPS) pour permettre à certbot de valider le domaine,
ou utiliser directement le plugin Apache de certbot :

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d transcription.example.com
# ou, plus simple si Apache est déjà configuré pour le domaine :
sudo certbot --apache -d transcription.example.com
```

Le renouvellement automatique est généralement déjà planifié par le paquet
`certbot` (timer systemd ou tâche cron). Vérifier avec :

```bash
sudo certbot renew --dry-run
```

## 5. Activer le site et recharger Apache

```bash
sudo a2ensite apache-transcription.conf
sudo apache2ctl configtest   # vérifie la syntaxe avant de recharger
sudo systemctl reload apache2
```

## 6. Démarrer l'application avec le port frontend correctement exposé

Le `docker-compose.yml` du projet expose déjà le conteneur `frontend` sur
`127.0.0.1:${FRONTEND_HOST_PORT:-8080}` (donc uniquement accessible depuis
la machine hôte, pas depuis l'extérieur — seul Apache doit pouvoir
l'atteindre). Aucune modification n'est nécessaire si vous gardez le port
par défaut (8080) ; sinon, ajustez `FRONTEND_HOST_PORT` dans `.env` **et**
la directive `ProxyPass` dans `apache-transcription.conf` en conséquence.

```bash
docker-compose up -d
```

## 7. Vérification

```bash
curl -I https://transcription.example.com
curl -I https://transcription.example.com/api/health
```

La première commande doit renvoyer la page d'accueil de l'application
(interface React), la seconde `{"status": "ok"}` via le proxy interne
`/api` du frontend vers le backend.
