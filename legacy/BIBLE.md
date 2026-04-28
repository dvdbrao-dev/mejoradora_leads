# OPENFANG BIBLE — Documento Maestro del Proyecto

> Última actualización: Marzo 2026
> Autor: Davidis Maximus
> Propósito: Referencia completa del sistema para contexto de IA y memoria persistente

---

## 1. QUÉ ES OPENFANG

Openfang es un pipeline de inteligencia comercial y ventas B2B automatizado para comercializar energía solar excedente de plantas fotovoltaicas en España.

El sistema localiza negocios cercanos a plantas solares, los filtra por potencial de compra, genera mensajes de prospección hiperpersonalizados y gestiona el seguimiento de cada lead.

**Tagline:** El War Room de la energía solar — estilo Palantir.

**Objetivo de negocio:** Vender energía solar excedente de 33 plantas fotovoltaicas a negocios locales de España antes de que expire o se pierda.

---

## 2. INFRAESTRUCTURA

**VPS:** dvdbrao@5.78.69.147
**SO:** Ubuntu 24 headless (Hetzner, IP alemana)
**RAM:** 4GB
**Directorio raíz:** ~/openfang/

**Variables de entorno (~/.bashrc):**
- ANTHROPIC_API_KEY
- OPENAI_API_KEY
- GOOGLE_PLACES_API_KEY
- FIRECRAWL_API_KEY

**Seguridad:**
- UFW activado
- API keys NUNCA en código — siempre en variables de entorno
- INCIDENTE PASADO: Key de OpenAI expuesta en chat — revocada y reemplazada
- INCIDENTE PASADO: Key de Firecrawl expuesta en chat — revocada y reemplazada

---

## 3. ESTRUCTURA DE ARCHIVOS

```
~/openfang/
├── agents/
│   ├── paco/system.md          ← Filtro y clasificación por tiers
│   ├── esther/system.md        ← Coordinación y contexto
│   ├── manolo/system.md        ← Copywriting con argumento geográfico
│   └── auditor/system.md       ← Revisión de calidad
├── data/
│   └── plants.json             ← 33 plantas fotovoltaicas con coordenadas
├── inputs/
│   ├── raw/                    ← CSVs del scraper (solar_FECHA.csv)
│   └── cleaned/                ← JSONs normalizados por ingest.py
├── outputs/
│   └── mensajes_TIMESTAMP.csv  ← Mensajes de Manolo listos para enviar
├── runs/
│   ├── *.json                  ← Historial completo de cada lead procesado
│   ├── enriched.json           ← Datos enriquecidos (teléfono, web, email)
│   └── lead_status.json        ← Estado de cada lead (pendiente/contactado/cerrado)
├── scripts/
│   ├── scraper.py              ← Scraper Google Maps (patchright/BeautifulSoup)
│   ├── scraper_solar.py        ← Scraper Places API por coordenadas de planta
│   ├── ingest.py               ← Normaliza CSV al schema estándar
│   ├── route.py                ← Pipeline principal de agentes
│   ├── enrich.py               ← Enriquecimiento con Places API Details
│   ├── enrich_web.py           ← Enriquecimiento de webs con Crawl4AI
│   ├── export_mensajes.py      ← Exporta mensajes de Manolo a CSV
│   ├── dashboard.py            ← Backend FastAPI del dashboard web
│   ├── start_dashboard.sh      ← Arranca dashboard en puerto 8080
│   ├── cron_scraper.sh
│   └── cron_solar.sh
└── dashboard/
    └── index.html              ← Dashboard web (accesible desde internet)
```

---

## 4. FLUJO COMPLETO DEL PIPELINE

```
1. SCRAPER SOLAR
   python3 scripts/scraper_solar.py --plants data/plants.json --api-key $GOOGLE_PLACES_API_KEY --radius 2000 --max-per-plant 20 --min-surplus 0
   → genera inputs/raw/solar_FECHA.csv

2. INGEST
   python3 scripts/ingest.py inputs/raw/ARCHIVO.csv
   → genera inputs/cleaned/ARCHIVO_FECHA.json (320 leads típico)

3. PIPELINE DE AGENTES
   python3 scripts/route.py inputs/cleaned/ARCHIVO.json
   → genera runs/*.json por cada lead procesado

4. ENRIQUECIMIENTO
   python3 scripts/enrich.py
   → llama a Places API Details para cada place_id → guarda teléfono/web en runs/enriched.json

   python3 scripts/enrich_web.py
   → usa Crawl4AI para extraer móviles de webs de negocios

5. EXPORTACIÓN
   python3 scripts/export_mensajes.py
   → genera outputs/mensajes_TIMESTAMP.csv
```

---

## 5. ARQUITECTURA DE AGENTES

### Modelos por agente
- Paco → GPT-4o-mini (filtro mecánico, barato)
- Esther → GPT-4o-mini (coordinación)
- Manolo → GPT-4o-mini (copy — migrar a Claude cuando haya flujo real)
- Auditor → GPT-4o-mini (revisión)

### Flujo condicional por tier
- **DISCARD** → para inmediatamente, guarda run
- **Tier C** → solo Paco, guarda run
- **Tier B** → Paco + Esther + Manolo (sin Auditor)
- **Tier A** → Paco + Esther + Manolo + Auditor

---

## 6. AGENTE PACO — REGLAS DE CLASIFICACIÓN

### DISCARD (solo estos casos)
**Franquicias restauración:** McDonald's, Burger King, KFC, Telepizza, Domino's, Subway, Starbucks, Foster's Hollywood, Five Guys, Popeyes, Vips, TGI Fridays

**Grandes superficies:** Mercadona, Lidl, Aldi, Carrefour, Alcampo, Eroski, El Corte Inglés, Hipercor

**Excepción supermercados:** Dia, Consum, Spar en franquicia independiente → Tier B

**Cadenas hoteleras:** ibis, NH, Meliá, Marriott, Hilton, Accor, B&B Hotel, Riu, Barceló, AC Hotels, Hyatt, Radisson, Holiday Inn, Novotel, Catalonia

**Excepción hoteles:** Hoteles con nombre propio → Tier A o B

**Corporaciones:** Amazon, BP, bp, Repsol, Cepsa, Shell, Galp, Endesa, Iberdrola, Naturgy

**Particulares**

### Regla fundamental
Falta de datos NUNCA es DISCARD → Tier B con confidence LOW

### Señal clave de encaje solar
Actividad diurna (8h-18h) = mejor encaje con energía solar

### Output JSON de Paco
```json
{
  "tier": "A|B|C|DISCARD",
  "opportunity": {"electricity": "...", "solar": "..."},
  "why": "2 frases",
  "missing_info": "...",
  "next_action": "...",
  "confidence_level": "HIGH|MEDIUM|LOW"
}
```

---

## 7. AGENTE MANOLO — REGLAS DE COPYWRITING

### Argumento principal
Distancia real a la planta solar — ningún competidor puede ofrecer esto.

### Humanización de distancia
- <0.5km → "en tu mismo barrio" / "a 5 minutos andando"
- 0.5-1.5km → "a menos de 2km"
- 1.5-3km → "a menos de 3km"
- >3km → usar con menos énfasis

### Personalización por sector (obligatoria)
- **Bodega:** "fermentación, frío de cámaras, maquinaria"
- **Taller:** "compresores, elevadores, soldadura"
- **Hotel:** "climatización, agua caliente, cocina"
- **Restaurante:** "cocina al mediodía, cámaras, aire"

### Output
Siempre 3 variantes: anti_venta, dolor_perdida, autoridad
Array JSON con 3 objetos. CRÍTICO: JSON siempre completo y cerrado.

---

## 8. SCRAPER SOLAR — scraper_solar.py

### Comando completo
```bash
python3 scripts/scraper_solar.py \
  --plants data/plants.json \
  --api-key $GOOGLE_PLACES_API_KEY \
  --radius 2000 \
  --max-per-plant 20 \
  --min-surplus 0
```

### Lógica
- Lee plants.json → agrupa por coordenadas idénticas → una llamada API por ubicación
- Places API Nearby Search con tipos: restaurant, bar, cafe, store, car_repair, city_hall, lodging, supermarket, storage
- Calcula distancia Haversine real
- Deduplica globalmente conservando planta con mayor surplus
- **place_id guardado en CSV** (añadido en marzo 2026) — extraído de result["name"].split("/")[-1]

### Columnas del CSV
lead_name, place_id, sector, address, municipality, province, phone, website, source, notes, plant_id, plant_name, plant_power_kw, plant_surplus_pct, distance_km

### Concepto surplus_percentage
- 100% = nadie ha comprado nada, máxima oportunidad
- 10% = casi todo vendido, poco disponible
- Hay que venderlo todo independientemente del % restante

---

## 9. PLANTAS FOTOVOLTAICAS (plants.json)

33 plantas en `/home/dvdbrao/openfang/data/plants.json`

| Zona | Plantas | Surplus destacado |
|------|---------|------------------|
| Torredelcampo | 2 | hasta 80.2% |
| Montilla | 4 | hasta 60.6% |
| Alcàsser | 1 | 71% |
| Plasencia | 2 | 45.9% |
| Madridejos | 2 | 43.6% |
| Baeza | 3 | 30% |
| Yecla | 3 | 30% |
| Azuqueca de Henares | 3 | 30% |
| Carmona | 2 | 30% |
| Sevilla I/II/III | 3 | variable |
| Jaén | 1 | 15.3% |
| Villanueva de la Serena | 1 | 2.8% |
| La Solana, Villacañas, Torrijos, Palma del Condado | varios | 30% |

**Actualización:** llega por email semanalmente, se sube con scp o nano al VPS.

---

## 10. ENRIQUECIMIENTO DE LEADS

### enrich.py — Places API Details
- Requiere place_id en los runs (disponible desde scraper actualizado en marzo 2026)
- Endpoint: GET https://places.googleapis.com/v1/places/{place_id}
- Fields: internationalPhoneNumber, websiteUri, regularOpeningHours, nationalPhoneNumber
- Guarda en runs/enriched.json: {place_id → {name, telefono, website, horario, tier}}

### enrich_web.py — Crawl4AI
- Para leads con website pero sin móvil español
- Usa AsyncWebCrawler para scrapear la web del negocio
- Extrae móviles ([67]\d{8}) y emails con regex
- Máximo 10 webs por ejecución

### ScrapeGraphAI — DESCARTADO
Intentado pero Google bloquea el scraping de resultados de búsqueda. 0/20 éxitos.

---

## 11. DASHBOARD WEB

- **Backend:** FastAPI en scripts/dashboard.py
- **Frontend:** dashboard/index.html (HTML + Leaflet + Chart.js + Tailwind)
- **Puerto:** 8080
- **Acceso:** http://5.78.69.147:8080

### Funcionalidades
- Lista de leads con tier, sector, planta, distancia, estado
- Mensajes de Manolo listos para copiar (3 variantes)
- Mapa Leaflet con plantas solares y leads
- Gráficas Chart.js (donut tiers, barras por planta)
- Estado de cada lead (pendiente/contactado/cerrado/no_interesa)
- Filtros por tier, estado, planta

### Arrancar
```bash
bash scripts/start_dashboard.sh
```

---

## 12. HERMES AGENT (instalado, pendiente de configurar)

- **Instalado en:** ~/.hermes/
- **Comando:** hermes
- **Propósito:** Agente autónomo de Nous Research — control de Openfang desde WhatsApp/móvil
- **Capacidades:** WhatsApp, Telegram, Slack, Discord nativos + memoria persistente + skills

### Pendiente
```bash
hermes gateway install   ← conectar WhatsApp
hermes setup             ← configurar modelo y canales
```

---

## 13. CRAWL4AI (instalado)

```python
from crawl4ai import AsyncWebCrawler
```
Instalado en el VPS. Playwright chromium configurado. Listo para usar en enrich_web.py.

---

## 14. ESTADO ACTUAL DEL PROYECTO (Marzo 2026)

### Completado ✅
- Scraper solar con place_id
- Pipeline de agentes (Paco → Esther → Manolo → Auditor)
- Flujo condicional por tier
- Dashboard web funcional
- enrich.py con Places API Details
- enrich_web.py con Crawl4AI
- Hermes Agent instalado

### Pendiente 🔄
- Conectar WhatsApp en Hermes Agent
- Probar enrich.py con runs que tienen place_id
- Probar enrich_web.py
- Reescribir prompt de Esther (GPT-4o-mini aplana su personalidad)
- Auditor demasiado estricto — siempre devuelve requiere_revisión
- Bug menor: run de DISCARD se guarda dos veces
- Seguimiento de leads contactados para no repetir
- Automatizar actualización semanal de plants.json

### % completado estimado
**~70%** del sistema funcional mínimo viable

---

## 15. REGLAS DEL PROYECTO

1. **Placeholders en código:** SIEMPRE avisar y usar el texto `"tu api aqui perro"`
2. **API keys:** NUNCA en código, NUNCA en el chat — solo en variables de entorno del VPS
3. **Codex:** Se usa para escribir y ejecutar código en el VPS
4. **Modelos:** GPT-4o-mini para agentes de bajo coste, Claude para Manolo cuando haya flujo real
5. **Surplus:** Hay que vender todo, independientemente del % disponible

---

## 16. COSTES ESTIMADOS

| Servicio | Coste mensual |
|----------|--------------|
| VPS Hetzner | ~15€ |
| OpenAI GPT-4o-mini (bajo volumen) | ~1-5€ |
| Google Places API | variable por uso |
| Firecrawl | plan gratuito (500 páginas/mes) |
| Total estimado | ~20-25€/mes |

---

## 17. COMANDOS DE REFERENCIA RÁPIDA

```bash
# Pipeline completo
python3 scripts/scraper_solar.py --plants data/plants.json --api-key $GOOGLE_PLACES_API_KEY --radius 2000 --max-per-plant 20 --min-surplus 0
python3 scripts/ingest.py inputs/raw/ARCHIVO.csv
python3 scripts/route.py inputs/cleaned/ARCHIVO.json
python3 scripts/enrich.py
python3 scripts/enrich_web.py
python3 scripts/export_mensajes.py

# Dashboard
bash scripts/start_dashboard.sh

# Hermes Agent
hermes
hermes gateway install

# Ver último run
ls -lt runs/ | head -5

# Ver stats rápidas
python3 -c "
import json, glob
runs = [f for f in glob.glob('runs/*.json') if 'enriched' not in f and 'status' not in f]
tiers = {}
for r in runs:
    t = json.load(open(r)).get('tier','?')
    tiers[t] = tiers.get(t,0) + 1
print(tiers)
"
```
