# Mejoradora Leads

Pipeline B2B para captar, clasificar, enriquecer y activar leads orientados a
comunidades solares Soldelia y cambio de comercializadora.

Estado auditado de referencia: `2026-04-23`

- VPS operativo: `dvdbrao@5.78.69.147`
- Repositorio: `dvdbrao-dev/mejoradora_leads`
- Repo activo: `~/mejoradora_leads`
- Vault Obsidian: `~/mejoradora-vault`

---

## Estado actual

El proyecto ya no se describe como `Openfang`. La identidad operativa vigente es
`Mejoradora Leads`, con repo activo en `~/mejoradora_leads` y documentación
operativa paralela en Obsidian.

Situación confirmada el `2026-04-23`:

- `410` leads auditados en `runs/`
- `4` Tier A
- `101` Tier B
- `74` Tier C
- `231` DISCARD
- `390` leads con teléfono
- `33` plantas Soldelia activas
- dashboard operativo en `:8001`
- cron semanal operativo
- SMS engine integrado con Dinahosting
- crédito SMS disponible: `50`
- vault Obsidian con `149` notas

El pipeline está funcional y el primer envío SMS está preparado, pendiente solo
de ejecución operativa.

---

## Qué Hay Hoy

El sistema convive con algunos elementos legacy, pero la base productiva actual
ya está definida:

- repo versionado en `~/mejoradora_leads`
- entorno virtual Python en `~/mejoradora_leads/.venv`
- variables de entorno centralizadas en `~/.env.mejoradora`
- vault operativo en `~/mejoradora-vault`
- runtime legado/auxiliar en `~/mejoradora_leads_data`
- fallback legacy todavía existente en `~/openfang`

Punto importante:

- aunque `MEJORADORA_LEADS_HOME` sigue existiendo, parte del código nuevo ya
  resuelve paths desde el repo activo
- el log SMS real no vive en `~/mejoradora_leads_data/logs/`
- el log SMS real es `~/mejoradora_leads/data/logs/sms_sent.jsonl`

---

## Stack

- Python 3.10
- FastAPI + Uvicorn
- OpenAI API
- Google Places API
- Crawl4AI
- Node.js 22 para piloto/bridge de WhatsApp
- Dinahosting API para SMS
- Makefile operativo para tareas frecuentes
- Obsidian vault para trazabilidad comercial y operativa

Dependencias Python declaradas hoy en `requirements.txt`:

- `jsonschema`
- `openai`
- `requests`
- `fastapi`
- `pydantic`
- `uvicorn[standard]`
- `crawl4ai`

Nota:

- `anthropic` no forma parte actualmente de `requirements.txt`

---

## Layout Real

### Repo

```text
~/mejoradora_leads
├── Makefile
├── README.md
├── data/
├── dashboard/
├── docs/
├── scripts/
├── schemas/
├── tests/
├── whatsapp/
├── runs/
└── outputs/
```

### Vault

```text
~/mejoradora-vault
├── Leads/
├── Plantas/
├── Sessions/
├── Infraestructura/
├── Procesos/
├── Desarrollo/
└── Scripts/
```

### Runtime legado / auxiliar

```text
~/mejoradora_leads_data
├── backups/
├── inputs/
├── logs/
├── outputs/
└── runs/
```

Regla vigente:

- el repo contiene código, configuración, datos versionados y documentación
- el vault contiene seguimiento operativo, sesiones y notas comerciales
- `~/mejoradora_leads_data` sigue existiendo para algunos flujos legacy

---

## Variables de Entorno

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
- `DINAHOSTING_USER`
- `DINAHOSTING_PASS`
- `DINAHOSTING_ACCOUNT`

`~/.bashrc` puede limitarse a:

```bash
source ~/.env.mejoradora
```

---

## Scripts Principales

Scripts operativos actuales en `scripts/`:

- `scraper_solar.py`
- `ingest.py`
- `route.py`
- `enrich.py`
- `enrich_web.py`
- `export_contact_queue.py`
- `export_mensajes.py`
- `manage_plants.py`
- `sms_engine.py`
- `validate_record.py`

Soporte adicional:

- `cron_scraper.sh`
- `cron_solar.sh`
- `cron_soldelia.sh`
- `start_dashboard.sh` (`legacy`, sigue apuntando a `8080`)

Dashboard productivo actual:

- `dashboard/dashboard.py`

---

## Flujo Operativo Actual

Flujo base:

1. captar leads con `scripts/scraper_solar.py`
2. normalizar e ingerir
3. rutear y clasificar con `scripts/route.py`
4. enriquecer con `scripts/enrich.py` y `scripts/enrich_web.py`
5. generar runs versionados en `runs/`
6. exportar cola comercial
7. preparar mensajes y primer contacto
8. reflejar estado operativo en Obsidian

Base de plantas vigente:

- `data/plants_soldelia.json`

Estado auditado del dataset:

- `33` plantas activas
- `410` leads generados
- `105` leads en Tier A+B
- `390` leads con teléfono entre todos los tiers

---

## Operación de Plantas y Leads

Resumen auditado a `2026-04-23`:

- Plantas activas: `33`
- Leads totales: `410`
- Tier A: `4`
- Tier B: `101`
- Tier C: `74`
- DISCARD: `231`
- Con teléfono: `390`
- Comisión estimada año 1 según dashboard: `5250 EUR`

Las cinco plantas que aparecen primero en el dashboard actual son:

- `CS Albacete I`
- `CS Alcalá de Guadaíra I`
- `CS Alcàsser I`
- `CS Azuqueca de Henares I`
- `CS Azuqueca de Henares II`

---

## Makefile Operativo

El repo incluye `Makefile` con comandos principales:

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

Notas importantes:

- `make pipeline` sigue apoyándose en `$(MEJORADORA_LEADS_HOME)` para ciertos flujos legacy
- `make export` genera cola comercial filtrada
- `make dashboard` todavía apunta al flujo legacy en `8080`
- la referencia operativa auditada para dashboard es `:8001`

---

## Arranque Mínimo

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

### 3. Arrancar dashboard productivo

```bash
cd ~/mejoradora_leads/dashboard
uvicorn dashboard:app --host 0.0.0.0 --port 8001
```

### 4. Verificar dashboard

```bash
curl http://localhost:8001/api/stats/soldelia
```

### 5. Ejecutar dry-run de SMS Tier A

```bash
cd ~/mejoradora_leads
python3 scripts/sms_engine.py --dry-run --tier A
```

### 6. Exportar cola comercial

```bash
make export
```

---

## SMS

El motor SMS ya está integrado con Dinahosting en:

- `scripts/sms_engine.py`

Estado auditado:

- crédito disponible: `50`
- log real: `data/logs/sms_sent.jsonl`
- mensajes Tier A validados en `dry-run`
- envíos reales todavía no ejecutados en el momento de esta auditoría

Ejemplos:

```bash
python3 scripts/sms_engine.py --dry-run --tier A
python3 scripts/sms_engine.py --tier A
```

Sincronización con vault:

```bash
python3 ~/mejoradora-vault/Scripts/sync_sms_status.py --vault ~/mejoradora-vault --log ~/mejoradora_leads/data/logs/sms_sent.jsonl --dry-run
```

---

## Obsidian Vault

El vault de Obsidian es parte del flujo operativo real.

Estado auditado:

- `149` notas totales
- `4` notas Tier A
- `101` notas Tier B
- `33` notas de plantas

Rutas relevantes:

- `~/mejoradora-vault/Sessions/2026-04-23-STATUS.md`
- `~/mejoradora-vault/Infraestructura/Accesos.md`
- `~/mejoradora-vault/Procesos/Restaurar-Servicios.md`
- `~/mejoradora-vault/Desarrollo/Próximos-Pasos.md`

---

## WhatsApp / Hermes

El bridge de WhatsApp sigue separado del pipeline principal.

Estado auditado:

- configuración Hermes detectada en `~/.hermes/config.yaml`
- logs detectados en `~/.hermes/logs/`
- bridge detectado en `~/.hermes/whatsapp/`
- no había procesos activos durante la auditoría

Todavía falta documentar el arranque real y validar sesión viva antes de usarlo
como canal operativo.

---

## Exportador

El exportador comercial formal actual es:

- `scripts/export_contact_queue.py`

Su objetivo es sacar una cola pequeña, verificable y utilizable para operación
manual antes de automatizar canales.

---

## Documentos Oficiales

Referencias vivas del repo:

- `ROADMAP.md`
- `ARCHITECTURE_DECISIONS.md`
- `PROJECT_STRUCTURE.md`
- `docs/PRODUCT_ARCHITECTURE.md`
- `BIBLE.md`
- `CLEANUP_PLAN.md`

Estos documentos deben prevalecer sobre notas históricas de etapas anteriores.

---

## Decisiones y Convivencia Legacy

El proyecto sigue en transición controlada:

- `~/openfang` existe todavía como fallback legacy
- `~/mejoradora_leads_data` sigue siendo usado por partes del tooling anterior
- el dashboard productivo actual ya no es el de `8080`
- el punto de referencia actual para operación es `dashboard/dashboard.py` en `8001`
- la identidad vigente del repositorio es `Mejoradora Leads`

La regla práctica es:

- usar `~/mejoradora_leads` como home activo
- tratar `~/openfang` y parte de `*_data` como compatibilidad, no como fuente principal

---

## Estado de Gitignore

El `.gitignore` excluye elementos sensibles u operativos como:

- `.env`
- `.venv/`
- `__pycache__/`
- `outputs/`
- caches y sesiones de WhatsApp
- runtime vivo no versionable

Los `runs/*.json` actuales sí forman parte del estado auditado del repo y no deben
tratarse automáticamente como basura operativa.

---

## Próximos Pasos Recomendados

- ejecutar el primer envío real de SMS Tier A
- sincronizar el vault tras ese envío
- verificar y documentar arranque real de Hermes
- revisar PRs abiertas `#1` y `#2`
- alinear `Makefile` y `start_dashboard.sh` con el puerto operativo `8001`
- seguir reduciendo supuestos legacy ligados a `openfang` y `*_data`
