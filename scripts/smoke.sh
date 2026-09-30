#!/bin/sh
set -eu
base_url=${BASE_URL:-http://127.0.0.1:8000}
frontend_url=${FRONTEND_URL:-http://127.0.0.1:8080}

check_live() {
  curl --fail --silent --show-error --retry 5 --retry-all-errors --retry-delay 1 "$base_url/api/v1/health/live" | grep -q '"alive"'
  echo 'Backend liveness smoke check passed.'
}

check_ready() {
  curl --fail --silent --show-error --retry 5 --retry-all-errors --retry-delay 1 "$base_url/api/v1/health/ready" | grep -q '"ready"'
  echo 'Backend readiness smoke check passed.'
}

check_frontend() {
  curl --fail --silent --show-error --retry 5 --retry-all-errors --retry-delay 1 "$frontend_url/" | grep -q 'CultureChamp'
  echo 'Frontend smoke check passed.'
}

case "${1:-all}" in
  live) check_live ;;
  ready) check_ready ;;
  frontend) check_frontend ;;
  all) check_live; check_ready; check_frontend ;;
  *) echo 'Unknown smoke check' >&2; exit 2 ;;
esac
