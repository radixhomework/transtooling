#!/usr/bin/env bash
#
# Checks that the application services respond correctly once
# `docker-compose up -d` has been run. Useful after a deployment or an
# update.
#
# Usage:
#   ./scripts/check-deployment.sh [base_url]
#
# Default base_url: http://127.0.0.1:8080 (direct access to the frontend
# container, without going through Apache — handy for a first local test).
# In production, call it with the public HTTPS URL instead, e.g:
#   ./scripts/check-deployment.sh https://transcription.example.com

set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8080}"

echo "== Deployment check on ${BASE_URL} =="

echo -n "1. Frontend reachable... "
if curl -fsS -o /dev/null "${BASE_URL}/"; then
  echo "OK"
else
  echo "FAIL"
  exit 1
fi

echo -n "2. Backend API reachable (via the frontend proxy)... "
HEALTH_RESPONSE=$(curl -fsS "${BASE_URL}/api/health" || echo "FAIL")
if [[ "${HEALTH_RESPONSE}" == *'"status":"ok"'* ]] || [[ "${HEALTH_RESPONSE}" == *'"status": "ok"'* ]]; then
  echo "OK"
else
  echo "FAIL (response: ${HEALTH_RESPONSE})"
  exit 1
fi

echo -n "3. Login with default admin account rejected without credentials... "
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/api/auth/login" \
  -H "Content-Type: application/json" -d '{"email":"","password":""}')
if [[ "${LOGIN_STATUS}" == "422" ]] || [[ "${LOGIN_STATUS}" == "401" ]]; then
  echo "OK (${LOGIN_STATUS})"
else
  echo "Unexpected status: ${LOGIN_STATUS} (check manually)"
fi

echo ""
echo "Basic checks completed successfully."
echo "Remember to check manually:"
echo "  - login with the admin account defined in .env"
echo "  - downloading at least one Whisper model from the admin panel"
echo "  - uploading a test audio file"
