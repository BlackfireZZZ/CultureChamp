#!/bin/sh
set -eu
base_url=${BASE_URL:-http://127.0.0.1:8000}
frontend_url=${FRONTEND_URL:-http://127.0.0.1:8080}

check_live() {
  check_response "$base_url/api/v1/health/live" '"alive"' 'Backend liveness'
  echo 'Backend liveness smoke check passed.'
}

check_ready() {
  check_response "$base_url/api/v1/health/ready" '"ready"' 'Backend readiness'
  echo 'Backend readiness smoke check passed.'
}

check_frontend() {
  check_response "$frontend_url/" 'Лад' 'Frontend'
  echo 'Frontend smoke check passed.'
}

check_response() {
  url=$1
  expected=$2
  label=$3
  if ! response=$(curl --noproxy '*' --fail --silent --show-error --retry 5 --retry-all-errors --retry-delay 1 "$url"); then
    echo "::error title=$label smoke::Cannot reach $url" >&2
    return 1
  fi
  if ! printf '%s' "$response" | grep -q "$expected"; then
    echo "::error title=$label smoke::Unexpected response from $url" >&2
    return 1
  fi
}

case "${1:-all}" in
  live) check_live ;;
  ready) check_ready ;;
  frontend) check_frontend ;;
  all) check_live; check_ready; check_frontend ;;
  *) echo 'Unknown smoke check' >&2; exit 2 ;;
esac
