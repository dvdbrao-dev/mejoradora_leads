# STATE OF PROJECT - OPENFANG

Auditoria: 2026-04-09

Objetivo de este mapa: permitir cambios grandes sin romper lo que ya existe. Estado real: **funcional con bloqueos**. No es una idea; ya hay scraper, ingesta, agentes, enriquecimiento, dashboard, runs historicos y WhatsApp experimental. El bloqueo esta en la salida comercial: export/contact queue/envio/seguimiento.

## Foto actual

Funciona hoy:
- `scripts/ingest.py` normaliza CSV/JSON; probado con `inputs/raw/ejemplo_leads.csv`.
- `scripts/route.py --help` arranca; orquesta Paco -> Esther -> Manolo -> Auditor.
- `scripts/enrich.py` arranca; en auditoria no encontro leads Tier A/B con `place_id` pendientes.
- `scripts/scraper_solar.py --help` y `scripts/scraper_custom_zone.py --help` arrancan.
- `dashboard/dashboard.py` importa; lee 33 plantas y 1094 leads desde `runs/`.
- `dashboard/index.html` existe.
- `schemas/record.schema.json` valida los 3 records de ejemplo en `data/records/examples/`.
- `whatsapp/server.js`, `whatsapp/connect.js`, `whatsapp/connect2.js` pasan chequeo de sintaxis.
- `whatsapp/send.py` compila.

Roto o inmaduro:
- `scripts/export_mensajes.py` falla con `AttributeError: 'list' object has no attribute 'get'`.
- Causa probable: lee `runs/*.json` como si todos fueran runs; `runs/whatsapp_sent.json` es una lista.
- `requirements.txt` esta incompleto: solo contiene `jsonschema`.
- Scripts con `requests` emiten warning de incompatibilidad urllib3/chardet/charset_normalizer.
- Habia 690 runs en `requiere_revisión`, 23 `aprobado`, 1 envio WhatsApp registrado y era `test_mode: true`.
- `whatsapp/send.py` tiene `TEST_MODE = True`.
- `README.md` y `phase_2.json` son planes viejos; no describen el sistema actual.
- No hay suite de tests automatizados.

## Flujo real

1. `data/plants.json`
2. `scripts/scraper_solar.py` / `scripts/scraper.py` / `scripts/scraper_custom_zone.py`
3. `inputs/raw/*.csv`
4. `scripts/ingest.py`
5. `inputs/cleaned/*.json`
6. `scripts/route.py` + `agents/*/system.md`
7. `runs/<lead>_<timestamp>.json`
8. `outputs/analysis/*.json` + `outputs/messages/*.json`
9. `scripts/enrich.py` / `scripts/enrich_web.py`
10. `runs/enriched.json`
11. `dashboard/dashboard.py` + `dashboard/index.html`
12. salida comercial prevista: `scripts/export_mensajes.py` / `whatsapp/server.js` / `whatsapp/send.py` / `runs/whatsapp_sent.json`

Donde se rompe ahora: despues de generar runs/mensajes. La exportacion no es robusta, WhatsApp esta en piloto y falta cola de contacto verificable.

## Convencion para cambios grandes

Preferir una rama por carril:
- `work/core-pipeline/<objetivo>`: scraper, ingest, route, agentes, schemas, enrich.
- `work/whatsapp/<objetivo>`: conexion, servidor local, envio, sesiones, log de envios.
- `work/dashboard/<objetivo>`: backend, frontend, endpoints y shim de dashboard.
- `work/contact-queue/<objetivo>`: export, cola, dedupe, estados, CSV/contactos.
- `work/experiments/<objetivo>`: pruebas no conectadas al flujo principal.

Si se trabaja sin rama, mantener un commit por carril. Los experimentos nuevos deben vivir en `experiments/` hasta que tengan contrato de entrada/salida; no meter prototipos nuevos directamente en `scripts/`.

## Clasificacion de archivos

### Codigo vivo: core pipeline

- `scripts/scraper_solar.py`
- `scripts/scraper_custom_zone.py`
- `scripts/scraper.py`
- `scripts/ingest.py`
- `scripts/route.py`
- `scripts/enrich.py`
- `scripts/enrich_web.py`
- `scripts/validate_record.py`
- `agents/paco/system.md`
- `agents/esther/system.md`
- `agents/manolo/system.md`
- `agents/auditor/system.md`
- `schemas/analysis.schema.json`
- `schemas/lead.schema.json`
- `schemas/master_record_v0.json`
- `schemas/message.schema.json`
- `schemas/record.schema.json`
- `data/plants.json`

### Codigo vivo: dashboard

- `dashboard/dashboard.py`
- `dashboard/index.html`
- `dashboard/__init__.py`
- `scripts/start_dashboard.sh`

### Codigo vivo/experimental: whatsapp

- `whatsapp/server.js`
- `whatsapp/send.py`
- `whatsapp/connect.js`
- `whatsapp/connect2.js`
- `whatsapp/package.json`
- `whatsapp/package-lock.json`

### Export/contact queue

- `scripts/export_mensajes.py` - actual, pero roto.
- futuro recomendado: `scripts/export_contact_queue.py` o `contact_queue/`.

### Compatibilidad o legado

- `scripts/dashboard.py` - shim para `scripts.dashboard:app`.
- `scripts/cron_scraper.sh` - automatizacion parcial.
- `scripts/cron_solar.sh` - automatizacion parcial.
- `README.md` - obsoleto.
- `phase_2.json` - plan antiguo; menciona script inexistente.
- `outputs/mensajes_*.csv` - exportaciones historicas.
- `/home/dvdbrao/openfang_nuevo/` - esqueleto antiguo fuera del repo principal.
- `/home/dvdbrao/.openfang/` - instalacion/plataforma distinta; no confundir con este repo.

### Datos operativos

No reformatear ni borrar dentro de cambios funcionales:
- `inputs/raw/*`
- `inputs/cleaned/*`
- `runs/*.json`
- `outputs/analysis/*`
- `outputs/messages/*`
- `outputs/mensajes_*.csv`

JSON auxiliares en `runs/` que NO son un run de lead:
- `runs/enriched.json`
- `runs/whatsapp_sent.json`
- `runs/lead_status.json` si aparece
- `runs/custom_searches.json` si aparece

Todo lector de `runs/*.json` debe validar tipo JSON y saltar indices/listas auxiliares.

### Basura o confusion: limpiar solo en rama separada

- `__pycache__/`
- `*.pyc`
- `dashboard/__pycache__/`
- `scripts/__pycache__/`
- `whatsapp/__pycache__/`
- `whatsapp/node_modules/`
- `whatsapp/.wwebjs_cache/`
- `whatsapp/auth_info/`
- `whatsapp/.wwebjs_auth/`
- duplicados historicos en `runs/`, `outputs/analysis/`, `outputs/messages/`

## Riesgos

- Falsa sensacion de avance: muchos leads/mensajes generados, casi ningun contacto real registrado.
- Dependencias no reproducibles: entorno instalado, `requirements.txt` minimo/falso.
- Riesgo de envio: cambiar WhatsApp de test a real puede mandar mensajes; revisar `TEST_MODE`, numero destino, servidor local y log.
- Riesgo de agregadores: `runs/` mezcla objetos run con indices/listas.
- Riesgo de repo: `whatsapp/node_modules/` estuvo/esta en el historial y ocupa mucho; no mezclar limpieza con feature.
- Riesgo de prompts: tocar `agents/*/system.md` cambia criterios comerciales y mensajes.

## Siguiente intervencion recomendada

No hacer mas scraping masivo todavia. Primero crear una cola de contacto pequena y verificable: 20 leads contactables, telefono, mensaje elegido, run origen, estado, fecha de contacto y resultado.
