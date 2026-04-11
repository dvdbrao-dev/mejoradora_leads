# Mejoradora Leads

Repo oficial: `dvdbrao-dev/mejoradora_leads`

Mejoradora Leads es un sistema de prospeccion B2B para localizar, calificar,
enriquecer y preparar contacto comercial sobre leads cercanos a plantas
fotovoltaicas.

La ruta local actual sigue siendo legacy: `/home/dvdbrao/openfang`. Eso se
mantiene temporalmente para no romper scripts ni runtime.

## Que hay hoy

- pipeline Python funcional para scraping, ingesta, calificacion y mensajes
- dashboard FastAPI + HTML
- bloque WhatsApp en piloto
- runtime historico local en `inputs/`, `runs/` y `outputs/`

## Regla estructural principal

El repo solo debe contener:

- codigo fuente
- configuracion versionable
- documentacion oficial
- ejemplos y fixtures pequenos

El runtime local no debe vivir en git:

- `inputs/raw/`
- `inputs/cleaned/`
- `runs/`
- `outputs/`
- sesiones/caches de WhatsApp

## Flujo actual

1. `data/plants.json`
2. `scripts/scraper_solar.py` o `scripts/scraper_custom_zone.py`
3. `inputs/raw/*.csv`
4. `scripts/ingest.py`
5. `inputs/cleaned/*.json`
6. `scripts/route.py`
7. `runs/<lead>_<timestamp>.json`
8. `outputs/analysis/*.json` y `outputs/messages/*.json`
9. `scripts/enrich.py` y opcionalmente `scripts/enrich_web.py`
10. `dashboard/dashboard.py`
11. piloto WhatsApp: `whatsapp/server.js` + `whatsapp/send.py`

## Operacion de plantas

La planta pasa a ser la unidad comercial principal.

Fuente oficial de verdad en esta iteracion:

- `data/plants.json`

Regla operativa:

- solo `status=active` participa por defecto en captacion
- solo `status=active` participa por defecto en exportacion comercial
- `full`, `paused`, `pending_data` y `archived` quedan fuera del flujo por defecto

CLI operativa:

```bash
python3 scripts/manage_plants.py list
python3 scripts/manage_plants.py active
python3 scripts/manage_plants.py add --name "CS Demo Norte" --lat 40.41 --lon -3.70 --municipality Madrid --province Madrid
python3 scripts/manage_plants.py set-status plant_12 full --note "Cupo completo"
python3 scripts/manage_plants.py validate
```

Flujo semanal recomendado:

1. alta de planta con `add` y estado inicial `pending_data`
2. completar datos operativos minimos
3. activar con `set-status <plant_id> active`
4. cuando deje de captar, marcar `full`
5. si debe salir del circuito, usar `paused` o `archived`

## Documentos oficiales

- `README.md`
- `CHANGELOG.md`
- `ROADMAP.md`
- `PROJECT_STRUCTURE.md`
- `ARCHITECTURE_DECISIONS.md`
- `CLEANUP_PLAN.md`

## Documentos legacy o de referencia

- `BIBLE.md`
- `legacy/openfang/STATE_OF_PROJECT_2026-04-09.md`
- `phase_2.json`

## Arranque minimo

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn scripts.dashboard:app --host 0.0.0.0 --port 8080
```

WhatsApp:

```bash
cd whatsapp
npm install
node server.js
```

## Variables vistas en el codigo actual

- `MEJORADORA_LEADS_HOME`
- `GOOGLE_PLACES_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

## Decisiones vigentes

- No migrar aun la carpeta fisica `openfang`.
- No refactorizar aun la logica del pipeline.
- No mezclar estados comerciales, de revision y de contacto.
- No usar documentos legacy como fuente oficial de verdad.

## Paths y runtime

La resolucion de ruta base ahora sigue esta politica:

1. usar `MEJORADORA_LEADS_HOME` si existe
2. si no existe, resolver relativo al repo actual
3. mantener compatibilidad con `/home/dvdbrao/openfang`

La lectura de `runs/` debe ignorar JSON auxiliares como `enriched.json`,
`lead_status.json`, `whatsapp_sent.json` y `custom_searches.json`.

El nuevo estado operativo propio de ContactQueue vive en:

```bash
runtime/contact_queue_state.json
```

Prioridad de estado:

1. `runtime/contact_queue_state.json`
2. mapeo legacy (`runs/lead_status.json`, `runs/whatsapp_sent.json`)
3. valores por defecto del contrato `ContactQueue`

## Exportador comercial

El exportador formal vive en:

```bash
python3 scripts/export_contact_queue.py
```

Filtros disponibles:

- `--tier A,B`
- `--review-status approved,needs_review`
- `--contact-status not_queued,contacted`
- `--commercial-status no_opportunity,lost`
- `--plant-id <id>`
- `--with-phone`
- `--preset ready_for_review|ready_for_contact|contacted_pending_followup|do_not_contact`
- `--limit N`
- `--format json|csv|both`

Ejemplo:

```bash
python3 scripts/export_contact_queue.py --tier A,B --with-phone --limit 50 --format both
```

Presets operativos:

- `ready_for_review`: `review_status in {pending, needs_review}` y `contact_status in {not_queued, queued, ready}`
- `ready_for_contact`: `review_status = approved`, `contact_status in {not_queued, queued, ready}` y `with_phone = true`
- `contacted_pending_followup`: `contact_status in {contacted, waiting_reply}`
- `do_not_contact`: `contact_status = do_not_contact`

Por defecto este exportador solo incluye leads ligados a plantas `active`.

Si hace falta revisar historico o plantas ya cerradas:

```bash
python3 scripts/export_contact_queue.py --include-non-active-plants
```

## Flujo manual de ContactQueue

Actualizar estado operativo manual:

```bash
python3 scripts/update_contact_queue_state.py <lead_id> \
  --owner paco \
  --review-status approved \
  --contact-status ready \
  --commercial-status opportunity_open \
  --next-action "revisar mensaje y validar telefono" \
  --notes "prioridad media"
```

Verificar el efecto en la cola:

```bash
python3 scripts/export_contact_queue.py --preset ready_for_contact --limit 20 --format json
```

## Smoke test

```bash
python3 scripts/manage_plants.py validate
python3 scripts/export_contact_queue.py --limit 10 --format json
python3 -m py_compile mejoradora_*.py scripts/*.py whatsapp/send.py dashboard/*.py
node --check whatsapp/server.js
```
