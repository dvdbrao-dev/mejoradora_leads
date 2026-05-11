#!/usr/bin/env bash
set -euo pipefail

PROJECT_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_HOME="${MEJORADORA_LEADS_HOME:-$HOME/mejoradora_leads_data}"
LOG_DIR="$DATA_HOME/logs"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/cron_soldelia_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

cd "$PROJECT_HOME"
export PYTHONPATH="$PROJECT_HOME${PYTHONPATH:+:$PYTHONPATH}"

echo "[$(date --iso-8601=seconds)] Iniciando cron Soldelia"
echo "PROJECT_HOME=$PROJECT_HOME"
echo "DATA_HOME=$DATA_HOME"

if [[ -f "$PROJECT_HOME/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$PROJECT_HOME/.venv/bin/activate"
fi

if [[ -f "$HOME/.env.mejoradora" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.env.mejoradora"
fi

PLANTS_PATH="${1:-data/plants.json}"
API_KEY="${2:-${GOOGLE_PLACES_API_KEY:-}}"
RADIUS="${3:-5000}"
MAX_PER_PLANT="${4:-30}"
MIN_SURPLUS="${5:-0}"

if [[ -z "$API_KEY" ]]; then
  echo "Falta GOOGLE_PLACES_API_KEY" >&2
  exit 1
fi

SCRAPE_LOG="$(mktemp)"
trap 'rm -f "$SCRAPE_LOG"' EXIT

python3 scripts/scraper_solar.py \
  --plants "$PLANTS_PATH" \
  --api-key "$API_KEY" \
  --radius "$RADIUS" \
  --max-per-plant "$MAX_PER_PLANT" \
  --min-surplus "$MIN_SURPLUS" | tee "$SCRAPE_LOG"

CSV_PATH="$(awk -F'OUTPUT_CSV=' '/OUTPUT_CSV=/{print $2}' "$SCRAPE_LOG" | tail -n 1)"
if [[ -z "$CSV_PATH" || ! -f "$CSV_PATH" ]]; then
  echo "No se encontró CSV generado para plants='$PLANTS_PATH'" >&2
  exit 1
fi

echo "CSV generado: $CSV_PATH"
python3 scripts/ingest.py "$CSV_PATH"

LATEST_CLEANED="$(
  ls -t \
    "$PROJECT_HOME"/inputs/cleaned/*.json \
    "$DATA_HOME"/inputs/cleaned/*.json 2>/dev/null | head -1
)"
if [[ -z "$LATEST_CLEANED" || ! -f "$LATEST_CLEANED" ]]; then
  echo "No se encontró JSON limpio tras ingest" >&2
  exit 1
fi

echo "Cleaned seleccionado: $LATEST_CLEANED"
python3 scripts/route.py "$LATEST_CLEANED"

python3 scripts/export_contact_queue.py \
  --tier A,B \
  --with-phone \
  --limit 100 \
  --format both \
  --output-name "soldelia_oficial_${TIMESTAMP}"

echo "[$(date --iso-8601=seconds)] Cron Soldelia finalizado"

# Instrucciones para crontab:
# 0 8 * * 1 /bin/bash /home/dvdbrao/mejoradora_leads/scripts/cron_soldelia.sh
