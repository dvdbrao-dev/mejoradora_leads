#!/bin/bash
set -euo pipefail

PROJECT_HOME="${MEJORADORA_LEADS_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$PROJECT_HOME"
uvicorn scripts.dashboard:app --host 0.0.0.0 --port 8080 --reload

# Para abrir el puerto: sudo ufw allow 8080
