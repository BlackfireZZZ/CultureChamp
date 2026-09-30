#!/bin/sh
set -eu
base_url=${BASE_URL:-http://localhost:8000}
frontend_url=${FRONTEND_URL:-http://localhost:8080}
curl --fail --silent --show-error "$base_url/api/v1/health/live" | grep -q '"alive"'
curl --fail --silent --show-error "$base_url/api/v1/health/ready" | grep -q '"ready"'
curl --fail --silent --show-error "$frontend_url/" | grep -q 'CultureChamp'
echo 'Stack smoke check passed.'
