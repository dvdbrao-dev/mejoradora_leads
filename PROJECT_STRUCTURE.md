# Project Structure

Auditoria: 2026-04-09

## Identidad

- Nombre oficial: **Mejoradora Leads**
- Repo oficial: `dvdbrao-dev/mejoradora_leads`
- Ruta local legacy temporal: `/home/dvdbrao/openfang`
- Nombre historico: **Openfang**

Regla: la identidad oficial del producto y del repo es **Mejoradora Leads**.
`openfang` solo se usa para explicar historia o para rutas que aun no se han
migrado.

## Documentos oficiales trackeados

Estos documentos deben quedar versionados si o si:

- `README.md`
- `ROADMAP.md`
- `PROJECT_STRUCTURE.md`
- `ARCHITECTURE_DECISIONS.md`
- `CLEANUP_PLAN.md`
- `.env.example`

Documentos no oficiales de producto:

- `BIBLE.md`: material historico Openfang.
- `STATE_OF_PROJECT.md`: auditoria puntual; no debe ser fuente oficial de
  verdad.
- `phase_2.json`: plan antiguo, obsoleto.

Decision recomendada sobre `STATE_OF_PROJECT.md`: **moverlo a legacy en el
proximo commit de archivo**, no mantenerlo como documento oficial de raiz.
Mientras no se mueva, tratarlo como auditoria de referencia, no como norma
vigente.

## Clasificacion oficial de rutas

### Codigo fuente

- `agents/`
- `dashboard/`
- `schemas/`
- `scripts/`
- `whatsapp/` solo para codigo y manifests:
  - `whatsapp/*.js`
  - `whatsapp/*.py`
  - `whatsapp/package.json`
  - `whatsapp/package-lock.json`
- `tests/`

Politica:
- debe versionarse
- no debe contener estado de ejecucion
- puede reorganizarse mas adelante sin cambiar logica ahora

### Configuracion

- `data/plants.json`
- `.env.example`
- futuros archivos en `config/`

Politica:
- debe versionarse
- debe ser pequena, revisable y sin secretos
- en el futuro deberia vivir bajo `config/` o `data/catalog/`

### Documentacion

- `README.md`
- `ROADMAP.md`
- `PROJECT_STRUCTURE.md`
- `ARCHITECTURE_DECISIONS.md`
- `CLEANUP_PLAN.md`

Politica:
- debe versionarse
- refleja realidad actual, no promesas

### Datos de entrada

- `inputs/raw/`
- `inputs/cleaned/`

Politica:
- por defecto no debe versionarse
- debe ignorarse
- puede conservar muestras anonimizadas y pequenas en `tests/fixtures/` o
  `data/examples/`

Movimiento futuro:
- mantener `inputs/` como runtime local
- mover fixtures utiles a `tests/fixtures/`

### Runtime local

- `runs/`
- `outputs/`
- `whatsapp/auth_info/`
- `whatsapp/.wwebjs_auth/`
- `whatsapp/.wwebjs_cache/`
- `whatsapp/node_modules/`
- caches, logs, `__pycache__/`

Politica:
- no debe versionarse
- debe ignorarse
- no debe mezclarse con codigo fuente

### Estado operativo

Hoy aparecen mezclados dentro de `runs/`:

- `runs/enriched.json`
- `runs/lead_status.json`
- `runs/whatsapp_sent.json`
- `runs/custom_searches.json` si existe

Politica objetivo:
- no deben versionarse a largo plazo
- deben tratarse como estado operativo local
- en el futuro deben moverse a una ruta especifica, por ejemplo:
  - `runtime/state/`
  - o `data/operational/` si se decide una persistencia revisable

Decision temporal:
- no moverlos todavia
- no romper dashboard ni scripts
- documentar que son indices auxiliares, no runs de lead

## Matriz repo vs runtime

| Ruta | Categoria | Versionar | Ignorar | Mover despues |
|---|---|---:|---:|---:|
| `agents/` | codigo fuente | si | no | no urgente |
| `dashboard/` | codigo fuente | si | no | no urgente |
| `scripts/` | codigo fuente | si | no | no urgente |
| `schemas/` | codigo fuente | si | no | no urgente |
| `whatsapp/*.js` `whatsapp/*.py` `package*.json` | codigo fuente | si | no | no urgente |
| `data/plants.json` | configuracion | si | no | opcional a `config/` |
| `inputs/raw/` | datos de entrada | no | si | mantener runtime |
| `inputs/cleaned/` | datos de entrada derivada | no | si | mantener runtime |
| `runs/` | runtime local | no | si | si |
| `runs/enriched.json` | estado operativo | no idealmente | si a futuro | si |
| `runs/lead_status.json` | estado operativo | no idealmente | si a futuro | si |
| `outputs/` | outputs | no | si | mantener runtime |
| `whatsapp/auth_info/` | credencial/sesion | no | si | no tocar ahora |
| `whatsapp/node_modules/` | runtime/dependencias instaladas | no | si | no aplica |

## Estructura oficial objetivo

Sin sobrearquitectura y sin mover carpetas aun:

```text
.
├── agents/                    # prompts de pipeline
├── dashboard/                 # API y frontend
├── scripts/                   # entrypoints y tareas manuales
├── whatsapp/                  # canal WhatsApp; solo codigo/manifests
├── schemas/                   # contratos JSON
├── data/
│   ├── plants.json            # catalogo versionado
│   └── records/examples/      # ejemplos versionados
├── tests/                     # tests y fixtures pequenos
├── docs/                      # opcional cuando crezca la documentacion
├── legacy/                    # archivo historico Openfang
├── inputs/                    # runtime local
├── runs/                      # runtime local
├── outputs/                   # runtime local
├── README.md
├── ROADMAP.md
├── PROJECT_STRUCTURE.md
├── ARCHITECTURE_DECISIONS.md
└── CLEANUP_PLAN.md
```

## Hardcodes legacy detectados

Hardcodes de ruta `openfang` vistos en codigo o scripts:

- `scripts/start_dashboard.sh`
- `scripts/enrich.py`
- `scripts/enrich_web.py`
- `scripts/export_mensajes.py`
- `scripts/validate_record.py`
- `scripts/cron_scraper.sh`
- `scripts/cron_solar.sh`
- `whatsapp/send.py`

Decision: convivir temporalmente con esa ruta, pero congelar nuevos hardcodes.
La estrategia de transicion esta descrita en `ARCHITECTURE_DECISIONS.md`.
