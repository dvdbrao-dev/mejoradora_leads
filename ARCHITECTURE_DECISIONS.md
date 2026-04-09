# Architecture Decisions

Auditoria: 2026-04-09

Este documento fija reglas estructurales y de dominio. No cambia la logica del
pipeline actual.

## 1. Documentos oficiales

Deben quedar trackeados:

- `README.md`
- `ROADMAP.md`
- `PROJECT_STRUCTURE.md`
- `ARCHITECTURE_DECISIONS.md`
- `CLEANUP_PLAN.md`
- `.env.example`

Documentos legacy o de referencia:

- `BIBLE.md`
- `STATE_OF_PROJECT.md`
- `phase_2.json`

### Decision sobre `STATE_OF_PROJECT.md`

Decision: **resumir lo util en docs oficiales y mover el archivo a legacy**.

Razon:
- es una auditoria puntual, no una norma estable
- mezcla observaciones, riesgos y planes de trabajo
- conserva la identidad Openfang y no debe competir con la arquitectura oficial

Accion recomendada en el siguiente commit de archivo:

```text
legacy/openfang/STATE_OF_PROJECT_2026-04-09.md
```

Hasta entonces:
- puede seguir en raiz como referencia temporal
- no debe citarse como documento oficial

## 2. Politica repo vs runtime

### Debe vivir en repo

- codigo fuente
- contratos y schemas
- configuracion versionable
- documentacion oficial
- ejemplos y fixtures pequenos

### Debe vivir fuera del repo

- entradas operativas reales
- resultados de ejecucion
- colas y estados runtime
- sesiones y credenciales
- dependencias instaladas
- caches y logs

### Decision especifica sobre rutas actuales

#### `runs/`

- categoria: runtime local
- no debe versionarse
- debe ignorarse
- en el futuro debe seguir existiendo como runtime, pero con separacion clara
  entre runs y estado operativo

#### `outputs/`

- categoria: outputs generados
- no debe versionarse
- debe ignorarse
- puede mantenerse como runtime local

#### `inputs/raw/`

- categoria: datos de entrada operativos
- no debe versionarse
- debe ignorarse
- ejemplos pequenos deben vivir en `tests/fixtures/` o `data/examples/`

#### `inputs/cleaned/`

- categoria: datos de entrada derivados
- no debe versionarse
- debe ignorarse
- puede mantenerse como runtime local mientras no haya pipeline formal de datos

#### `runs/enriched.json`

- categoria: estado operativo
- recomendacion final: no versionarlo
- decision temporal: no moverlo todavia para no romper scripts
- movimiento futuro recomendado: `runtime/state/enriched.json`

#### `runs/lead_status.json`

- categoria: estado operativo
- recomendacion final: no versionarlo
- decision temporal: no moverlo todavia para no romper dashboard
- movimiento futuro recomendado: `runtime/state/lead_status.json`

## 3. Modelo oficial del dominio

Este es el modelo de verdad recomendado. No implica base de datos aun.

### Plant

Representa una planta o fuente comercial de energia asociada al lead.

Modelo oficial de esta iteracion:

- `plant_id` obligatorio
- `name` obligatorio
- `lat` obligatorio
- `lon` obligatorio
- `address` opcional
- `municipality` opcional
- `province` opcional
- `autonomous_community` opcional
- `postal_code` opcional
- `radio_km` obligatorio
- `energy_available_kwh` opcional
- `target_min_consumption_kwh_year` opcional
- `solar_price_eur_kwh` opcional
- `community_name` opcional
- `status` obligatorio
- `notes` opcional
- `created_at` obligatorio
- `updated_at` obligatorio

Campos de compatibilidad temporal permitidos mientras siga vivo el pipeline actual:

- `power_kw`
- `surplus_percentage`

### Lead

Representa el negocio objetivo contactable.

Campos recomendados:

- `lead_id`
- `name`
- `sector`
- `location.address`
- `location.municipality`
- `location.province`
- `contact.phone`
- `contact.email`
- `contact.contact_name`
- `contact.contact_role`
- `source`
- `source_ref`
- `place_id`
- `website`
- `assigned_plant_id`
- `distance_km`
- `energy_signal`
- `created_at`
- `updated_at`

### Qualification

Representa el resultado de analisis del lead. Debe ser separada del Lead.

Campos recomendados:

- `qualification_id`
- `lead_id`
- `tier`
- `score`
- `reason_summary`
- `roof_possible`
- `estimated_consumption_band`
- `fit_summary`
- `risk_flags[]`
- `review_status`
- `qualified_by`
- `qualified_at`
- `model_used`

### ContactQueue

Representa una unidad operativa lista para contacto o seguimiento.

Campos recomendados:

- `queue_id`
- `lead_id`
- `qualification_id`
- `priority`
- `channel`
- `proposed_message`
- `message_variant`
- `assigned_to`
- `contact_status`
- `next_action_at`
- `last_contact_at`
- `contact_attempts`
- `run_ref`
- `notes`
- `created_at`
- `updated_at`

### CommercialStatus

Representa el estado comercial de la oportunidad, separado del contacto.

Campos recomendados:

- `lead_id`
- `sales_stage`
- `opportunity_status`
- `estimated_value`
- `last_result`
- `owner`
- `opened_at`
- `updated_at`
- `closed_at`
- `close_reason`

## 4. Estados oficiales

Regla: no mezclar dimensiones. Un lead puede tener al mismo tiempo:

- una clasificacion
- un estado de enriquecimiento
- un estado de revision
- un estado de contacto
- un estado comercial

### Clasificacion de lead

Usar solo:

- `A`
- `B`
- `C`
- `DISCARD`

Significado:

- `A`: alta prioridad comercial
- `B`: interesante, pero no inmediata
- `C`: bajo valor o baja claridad
- `DISCARD`: fuera de objetivo

### Estado de enriquecimiento

Usar solo:

- `pending`
- `partial`
- `complete`
- `failed`

### Estado de planta

Usar solo:

- `active`
- `full`
- `paused`
- `pending_data`
- `archived`

Significado:

- `active`: planta apta para captacion y exportacion por defecto
- `full`: planta completa; no debe captar ni exportar nuevos leads
- `paused`: planta temporalmente parada; no debe entrar en flujo por defecto
- `pending_data`: alta hecha pero faltan datos operativos para activarla
- `archived`: planta fuera de operacion; solo historico

Regla central:

- solo `active` participa por defecto en captacion y exportacion

## 5. Fuente de verdad de plantas

Decision vigente:

- usar `data/plants.json` como catalogo oficial y operativo de plantas
- no introducir aun base de datos
- no separar todavia un `runtime/state` especifico para plantas porque el volumen y
  la frecuencia de cambio no lo justifican

Razon:

- permite alta y cambios por CLI desde SSH/Codex
- es barato, legible y versionable
- evita romper el pipeline actual con una migracion prematura a BD

### Estado de revision

Usar solo:

- `pending`
- `approved`
- `needs_review`
- `rejected`

### Estado de contacto

Usar solo:

- `not_queued`
- `queued`
- `ready`
- `contacted`
- `waiting_reply`
- `responded`
- `do_not_contact`

### Estado comercial/venta

Usar solo:

- `no_opportunity`
- `opportunity_open`
- `qualified_opportunity`
- `proposal_sent`
- `negotiation`
- `won`
- `lost`

## 5. Convivencia con la ruta legacy

Ruta actual:

```text
/home/dvdbrao/openfang
```

Decision:
- mantenerla temporalmente
- no introducir nuevos hardcodes
- preparar una capa de configuracion antes de migrar fisicamente

### Hardcodes detectados

- `scripts/start_dashboard.sh`
- `scripts/enrich.py`
- `scripts/enrich_web.py`
- `scripts/export_mensajes.py`
- `scripts/validate_record.py`
- `scripts/cron_scraper.sh`
- `scripts/cron_solar.sh`
- `whatsapp/send.py`

### Estrategia futura de migracion

1. Introducir una unica variable de ruta base:
   - `MEJORADORA_LEADS_HOME`

2. Regla de resolucion:
   - si existe `MEJORADORA_LEADS_HOME`, usarla
   - si no, derivar desde `__file__` o desde la raiz del repo
   - mantener compatibilidad con `/home/dvdbrao/openfang` mientras dure la
     transicion

3. Sustituir hardcodes por lotes pequenos:
   - dashboard/start scripts
   - enrich/export
   - cron y WhatsApp

4. Cuando no queden hardcodes:
   - renombrar carpeta fisica a una ruta nueva
   - validar dashboard, enrich, export y WhatsApp

5. Solo despues:
   - limpiar referencias legacy de documentacion residual

## 6. Politica de paths

Variable oficial:

- `MEJORADORA_LEADS_HOME`

Resolucion:

1. usar `MEJORADORA_LEADS_HOME` si existe
2. si no existe, resolver desde la ruta del propio archivo y la raiz del repo
3. si aun no puede resolverse, mantener compatibilidad con la ruta legacy
   `/home/dvdbrao/openfang`

Regla:
- no introducir nuevos hardcodes `~/openfang`
- los scripts existentes deben migrar a la resolucion comun

## 7. Politica de lectura de runs

`runs/` contiene dos familias distintas:

- run records validos del pipeline
- JSON auxiliares de estado o indices

JSON auxiliares conocidos:

- `enriched.json`
- `lead_status.json`
- `whatsapp_sent.json`
- `custom_searches.json`

Un run record valido debe cumplir como minimo:

- ser un objeto JSON
- tener `lead` como objeto
- tener identidad de lead (`lead_id` o `lead_name`)
- tener al menos una senal de pipeline como `status`, `started_at`, `paco`,
  `esther`, `manolo` o `auditor`

Todo lector nuevo de `runs/` debe usar esta regla y no asumir que
`runs/*.json` son todos runs.

## 8. Contrato inicial de ContactQueue

Implementacion actual:

- modulo: `mejoradora_contact_queue.py`
- estructura: `ContactQueueItem`

Campos obligatorios:

- `queue_id`
- `lead_id`
- `business_name`
- `tier`
- `review_status`
- `contact_status`
- `commercial_status`
- `created_at`
- `updated_at`

Campos opcionales:

- `plant_id`
- `category`
- `distance_km`
- `estimated_consumption_band`
- `phone`
- `website`
- `suggested_channel`
- `message_preview`
- `reason_fit`
- `owner`

Estado inicial por defecto:

- `contact_status = not_queued`
- `commercial_status = no_opportunity`

Este contrato sirve para construir la futura cola comercial real sin depender
de estructuras ambiguas de runtime.

## 9. Mapeo canonico de estados legacy

Implementacion actual:

- modulo: `mejoradora_statuses.py`

### `review_status`

- `aprobado` -> `approved`
- `requiere_revisión` / `requiere_revision` -> `needs_review`
- `descartado_por_paco` -> `rejected`
- `tier_c_en_espera` -> `pending`
- ausencia de estado -> `pending`

### `contact_status`

- `lead_status.json = pendiente` -> `queued`
- `lead_status.json = contactado` -> `contacted`
- `lead_status.json = cerrado` -> `responded`
- `lead_status.json = no_interesa` -> `do_not_contact`
- presencia en `whatsapp_sent.json` sin override manual -> `contacted`
- sin senales legacy -> `not_queued`

Ambiguedades resueltas:

- `cerrado` no se trata como venta ganada; se interpreta como ciclo de contacto
  cerrado porque el estado legacy no separa contacto y venta.
- `pendiente` se interpreta como cola operativa pendiente, no como ausencia de cola.

### `commercial_status`

No existe hoy una fuente legacy fiable de estado comercial.

Decision:

- `lead_status.json = no_interesa` -> `lost`
- todo lo demas -> `no_opportunity`

Esto evita mezclar contacto con ventas mientras no exista un estado comercial
real separado.
