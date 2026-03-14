#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

run_and_ingest() {
  local query="$1"
  local zona="$2"
  local max_results="$3"

  local log_file
  log_file="$(mktemp)"

  python3 scripts/scraper.py --query "$query" --zona "$zona" --max "$max_results" | tee "$log_file"

  local csv_path
  csv_path="$(awk -F'OUTPUT_CSV=' '/OUTPUT_CSV=/{print $2}' "$log_file" | tail -n 1)"
  rm -f "$log_file"

  if [[ -z "$csv_path" || ! -f "$csv_path" ]]; then
    echo "No se encontró CSV generado para query='$query' zona='$zona'" >&2
    exit 1
  fi

  python3 scripts/ingest.py "$csv_path"
}

run_and_ingest "bares" "Granada, España" 50
run_and_ingest "talleres mecánicos" "Granada, España" 50

# Instrucciones para crontab:
# 1) Ejecuta: crontab -e
# 2) Añade esta línea (en una sola línea) para correr cada 3 días a las 06:00:
# 0 6 */3 * * /bin/bash /home/dvdbrao/openfang/scripts/cron_scraper.sh >> /home/dvdbrao/openfang/runs/cron_scraper.log 2>&1
