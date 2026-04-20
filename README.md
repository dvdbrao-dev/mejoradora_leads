# Mejoradora Leads

Pipeline B2B para generar, calificar, enriquecer y exportar leads orientados a
la venta de membresias para comunidades solares y cambio de comercializadora.

VPS operativo: `dvdbrao@5.78.69.147`
Repositorio: `dvdbrao-dev/mejoradora_leads`

---

## Estado actual

El proyecto esta desplegado en el VPS y ya tiene una separacion clara entre:

- repo versionado en `~/mejoradora_leads`
- runtime local en `~/mejoradora_leads_data`
- entorno virtual Python en `~/mejoradora_leads/.venv`
- variables de entorno centralizadas en `~/.env.mejoradora`

El runtime operativo ya no debe vivir en git. Los inputs, runs, logs, backups y
outputs se guardan fuera del repo.

---

## Stack

- Python 3.10
- FastAPI + Uvicorn
- OpenAI API
- Google Places API
- Crawl4AI
- Node.js 22 para el piloto de WhatsApp Web
- Makefile operativo para tareas frecuentes

Dependencias Python declaradas hoy en `requirements.txt`:

- `jsonschema`
- `openai`
- `requests`
- `fastapi`
- `pydantic`
- `uvicorn[standard]`
- `crawl4ai`

Nota: `anthropic` no forma parte actualmente de `requirements.txt`.

---

## Layout real

### Repo

```text
~/mejoradora_leads
├── Makefile
├── README.md
├── requirements.txt
├── data/
├── scripts/
├── whatsapp/
├── dashboard/
├── tests/
├── inputs/
├── runs/
└── outputs/
```

### Runtime local

```text
~/mejoradora_leads_data
├── README.md
├── backups/
├── inputs/
│   ├── raw/
│   └── cleaned/
├── logs/
├── outputs/
│   ├── analysis/
│   └── messages/
└── runs/
```

Regla vigente:

- el repo contiene codigo, configuracion y documentacion
- `~/mejoradora_leads_data` contiene datos operativos y artefactos del pipeline

---

## Variables de entorno

Las API keys y paths ya no viven hardcodeadas en `~/.bashrc`.

Fuente activa actual:

- `~/.env.mejoradora`

Variables relevantes:

- `MEJORADORA_LEADS_HOME`
- `OPENAI_API_KEY`
- `GOOGLE_PLACES_API_KEY`
- `FIRECRAWL_API_KEY`
- `GEMINI_API_KEY`
- `OPENROUTER_API_KEY`
- `NVIDIA_API_KEY`

`~/.bashrc` solo hace:

```bash
source ~/.env.mejoradora
```

---

## Scripts principales

Los scripts operativos actuales en `scripts/` son:

- `scraper_solar.py`
- `scraper_custom_zone.py`
- `ingest.py`
- `route.py`
- `enrich.py`
- `enrich_web.py`
- `export_contact_queue.py`
- `export_mensajes.py`
- `manage_plants.py`
- `dashboard.py`
- `validate_record.py`

Soporte adicional:

- `cron_scraper.sh`
- `cron_solar.sh`
- `start_dashboard.sh`

---

## Flujo operativo actual

Flujo base:

1. captar leads con `scripts/scraper_solar.py` o `scripts/scraper_custom_zone.py`
2. guardar bruto en `~/mejoradora_leads_data/inputs/raw/`
3. normalizar e ingerir
4. generar JSON limpios en `~/mejoradora_leads_data/inputs/cleaned/`
5. rutear y clasificar con `scripts/route.py`
6. generar runs en `~/mejoradora_leads_data/runs/`
7. enriquecer con `scripts/enrich.py` y `scripts/enrich_web.py`
8. exportar cola comercial y mensajes

La base de plantas actual vive en:

- `data/plants.json`

---

## Makefile operativo

El repo ya incluye `Makefile` con comandos principales:

```bash
make help
make install
make dashboard
make scrape
make pipeline
make enrich
make export
make status
make plants
make clean-logs
make backup
make test
```

Comportamiento esperado:

- `make pipeline` toma el ultimo JSON disponible en `$(MEJORADORA_LEADS_HOME)/inputs/cleaned/`
- `make export` genera cola comercial filtrada
- `make dashboard` expone FastAPI en puerto `8080`

---

## Arranque rapido

### 1. Activar entorno

```bash
cd ~/mejoradora_leads
source .venv/bin/activate
source ~/.env.mejoradora
```

### 2. Ver ayuda operativa

```bash
make help
```

### 3. Arrancar dashboard

```bash
make dashboard
```

### 4. Ejecutar pipeline sobre el ultimo cleaned

```bash
make pipeline
```

### 5. Exportar cola comercial

```bash
make export
```

---

## WhatsApp

El piloto de WhatsApp sigue separado en `whatsapp/`.

Archivos relevantes:

- `whatsapp/server.js`
- `whatsapp/send.py`
- `whatsapp/connect.js`
- `whatsapp/connect2.js`

No se deben versionar sesiones ni caches de WhatsApp.

---

## Estado de gitignore

El `.gitignore` actual ya excluye elementos sensibles u operativos como:

- `.env`
- `.venv/`
- `__pycache__/`
- `inputs/raw/`
- `inputs/cleaned/*.json`
- `runs/*.json`
- `outputs/`
- caches y sesiones de WhatsApp

La intencion sigue siendo mantener el runtime fuera del repo.

---

## Estado real del entorno en abril de 2026

Confirmado en el VPS:

- disco saneado y con espacio libre suficiente
- `python3.10-venv` instalado
- `.venv` creada correctamente
- imports `fastapi`, `openai` y `uvicorn` funcionando
- `anthropic` no instalado por defecto
- `make help` funcional
- `Makefile` ya committeado en git

---

## Proximos pasos recomendados

- ajustar scripts para leer siempre de `MEJORADORA_LEADS_HOME`
- revisar si `inputs/`, `runs/` y `outputs/` del repo deben quedarse solo como legacy
- anadir `anthropic` a `requirements.txt` solo si vuelve a usarse
- limpiar coincidencias de secretos dentro de `.venv` cuando no hagan falta paquetes pesados
