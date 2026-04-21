# ============================================================
# MEJORADORA LEADS — Makefile
# VPS: dvdbrao@5.78.69.147
# Actualizado: abril 2026
# ============================================================

SHELL := /bin/bash
VENV := .venv/bin/activate
DATA := $(MEJORADORA_LEADS_HOME)

.PHONY: help install dashboard scrape pipeline enrich export status plants clean-logs backup test

help: ## Muestra este menu
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  DATA DIR: $(DATA)"

install: ## Instala dependencias Python y Node (whatsapp)
	source $(VENV) && pip install -r requirements.txt --quiet
	cd whatsapp && npm install --silent 2>/dev/null || true
	@echo "Dependencias instaladas OK"

dashboard: ## Arranca el dashboard FastAPI en puerto 8080
	source $(VENV) && uvicorn scripts.dashboard:app --host 0.0.0.0 --port 8080 --reload

scrape: ## Scraping solar con radio 5000m (plantas Soldelia activas)
	source $(VENV) && python3 scripts/scraper_solar.py \
		--plants data/plants_soldelia.json \
		--api-key $$GOOGLE_PLACES_API_KEY \
		--radius 5000 \
		--max-per-plant 30 \
		--min-surplus 0

pipeline: ## Ejecuta pipeline completo sobre ultimo archivo cleaned
	$(eval FILE := $(shell ls -t $(DATA)/inputs/cleaned/*.json 2>/dev/null | head -1))
	@if [ -z "$(FILE)" ]; then echo "ERROR: no hay archivos en inputs/cleaned/"; exit 1; fi
	@echo "Procesando: $(FILE)"
	source $(VENV) && python3 scripts/route.py $(FILE)

enrich: ## Enriquece leads con Places API y Crawl4AI
	source $(VENV) && python3 scripts/enrich.py
	source $(VENV) && python3 scripts/enrich_web.py

export: ## Exporta cola de contacto Tier A y B con telefono
	source $(VENV) && python3 scripts/export_contact_queue.py \
		--tier A,B \
		--with-phone \
		--limit 100 \
		--format both

status: ## Stats rapidas de runs (tiers, totales)
	@source $(VENV) && python3 -c "\
import json, glob, os; \
data = os.environ.get('MEJORADORA_LEADS_HOME', os.path.expanduser('~/mejoradora_leads_data')); \
runs = [f for f in glob.glob(f'{data}/runs/*.json') if not any(x in f for x in ['enriched','status','whatsapp','custom'])]; \
tiers = {}; \
[tiers.update({json.load(open(r)).get('tier','?'): tiers.get(json.load(open(r)).get('tier','?'),0)+1}) for r in runs]; \
print('TIERS:', tiers); \
print('TOTAL:', sum(tiers.values()))"

plants: ## Lista plantas Soldelia configuradas
	source $(VENV) && python3 scripts/manage_plants.py list 2>/dev/null || \
		python3 -c "import json; plants=json.load(open('data/plants_soldelia.json')); \
		[print(f\"{p['plant_id']:30} {p['status']:10} {p.get('priority','?'):8} CR:{p.get('coeficiente_reparto',0):.0%}\") for p in plants]" \
		2>/dev/null || echo "plants_soldelia.json aun no existe"

clean-logs: ## Borra logs de mas de 30 dias
	find $(DATA)/logs -name "*.log" -mtime +30 -delete 2>/dev/null || true
	@echo "Logs antiguos borrados"

backup: ## Backup de runs e inputs a backups/
	tar -czf $(DATA)/backups/backup_$$(date +%Y%m%d_%H%M).tar.gz \
		$(DATA)/runs/ $(DATA)/inputs/ 2>/dev/null
	@echo "Backup creado en $(DATA)/backups/"

test: ## Run tests
	@source $(VENV) && python3 tests/test_dashboard.py
