#!/usr/bin/env bash
#
# Vérifie que les services de l'application répondent correctement, une fois
# `docker-compose up -d` lancé. Utile après un déploiement ou une mise à jour.
#
# Usage :
#   ./scripts/check-deployment.sh [base_url]
#
# base_url par défaut : http://127.0.0.1:8080 (accès direct au conteneur
# frontend, sans passer par Apache — pratique pour un premier test local).
# En production, appeler plutôt avec l'URL HTTPS publique, ex:
#   ./scripts/check-deployment.sh https://transcription.example.com

set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8080}"

echo "== Vérification du déploiement sur ${BASE_URL} =="

echo -n "1. Frontend accessible... "
if curl -fsS -o /dev/null "${BASE_URL}/"; then
  echo "OK"
else
  echo "ÉCHEC"
  exit 1
fi

echo -n "2. API backend accessible (via proxy frontend)... "
HEALTH_RESPONSE=$(curl -fsS "${BASE_URL}/api/health" || echo "ÉCHEC")
if [[ "${HEALTH_RESPONSE}" == *'"status":"ok"'* ]] || [[ "${HEALTH_RESPONSE}" == *'"status": "ok"'* ]]; then
  echo "OK"
else
  echo "ÉCHEC (réponse: ${HEALTH_RESPONSE})"
  exit 1
fi

echo -n "3. Login avec le compte admin par défaut refusé sans identifiants... "
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/api/auth/login" \
  -H "Content-Type: application/json" -d '{"email":"","password":""}')
if [[ "${LOGIN_STATUS}" == "422" ]] || [[ "${LOGIN_STATUS}" == "401" ]]; then
  echo "OK (${LOGIN_STATUS})"
else
  echo "Statut inattendu : ${LOGIN_STATUS} (à vérifier manuellement)"
fi

echo ""
echo "Vérifications de base terminées avec succès."
echo "Pensez à vérifier manuellement :"
echo "  - la connexion avec le compte admin défini dans .env"
echo "  - le téléchargement d'au moins un modèle Whisper depuis le panneau admin"
echo "  - un envoi de fichier audio de test"
