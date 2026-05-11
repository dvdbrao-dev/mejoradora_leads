#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

run_and_ingest() {
  local plants_path="$1"
  local api_key="$2"
  local radius="$3"
  local max_per_plant="$4"
  local min_surplus="$5"

  if [[ -z "$api_key" ]]; then
    echo "Falta API key. Define GOOGLE_PLACES_API_KEY o pásala como segundo argumento." >&2
    exit 1
  fi

  local log_file
  log_file="$(mktemp)"

  PYTHONPATH="$ROOT_DIR" python3 scripts/scraper_solar.py \
    --plants "$plants_path" \
    --api-key "$api_key" \
    --radius "$radius" \
    --max-per-plant "$max_per_plant" \
    --min-surplus "$min_surplus" | tee "$log_file"

  local csv_path
  csv_path="$(awk -F'OUTPUT_CSV=' '/OUTPUT_CSV=/{print $2}' "$log_file" | tail -n 1)"
  rm -f "$log_file"

  if [[ -z "$csv_path" || ! -f "$csv_path" ]]; then
    echo "No se encontró CSV generado para plants='$plants_path'" >&2
    exit 1
  fi

  python3 scripts/ingest.py "$csv_path"
}

PLANTS_PATH="${1:-data/plants.json}"
API_KEY="${2:-${GOOGLE_PLACES_API_KEY:-}}"
RADIUS="${3:-5000}"
MAX_PER_PLANT="${4:-30}"
MIN_SURPLUS="${5:-0}"

run_and_ingest "$PLANTS_PATH" "$API_KEY" "$RADIUS" "$MAX_PER_PLANT" "$MIN_SURPLUS"

# Instrucciones para crontab:
# 1) Ejecuta: crontab -e
# 2) Añade esta línea (en una sola línea) para correr cada 3 días a las 06:00:
# 0 6 */3 * * MEJORADORA_LEADS_HOME=/home/dvdbrao/openfang /bin/bash /home/dvdbrao/openfang/scripts/cron_scraper.sh >> /home/dvdbrao/openfang/runs/cron_scraper.log 2>&1
