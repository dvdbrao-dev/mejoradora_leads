# MEJORADORA LEADS — Arquitectura de Producto
## Sistema de captación comercial para comunidades solares Soldelia
> v1.0 · 21 Abril 2026 · Objetivo: licenciar a Soldelia

## FLUJO COMERCIAL
1. SCRAPING — Google Places API, 5km radio por planta
2. CLASIFICACIÓN — Agente Paco (A/B/C/DISCARD)
3. PRE-CONTACTO SMS — Automático a Tier A+B con teléfono
4. TRACKING — Entregado, leído, respondido, no_interesa
5. FOLLOW-UP WHATSAPP — Si responde positivo, pitch Manolo
6. AGENDAR — Visita/llamada via Google Calendar + ruta optimizada
7. VISITA — Recoger factura eléctrica
8. ESTUDIO — Calcular ahorro con datos reales CUPS
9. CIERRE — Contrato firmado, alta en Soldelia
10. LIQUIDACIÓN — kWh × 0.00639€ mensual

## ESTADO ACTUAL
- ✅ Scraping (33 plantas, cron semanal)
- ✅ Clasificación (Paco operativo)
- ✅ Export leads (105 A+B, 98 con tel)
- ✅ Dashboard + tests
- ✅ Hermes Agent (Telegram + WhatsApp)
- ⏳ SMS Engine (proveedor local confirmado, integración pendiente)
- ⏳ WhatsApp follow-up automático
- ⏳ Google Calendar para visitas
- ⏳ CRM funnel visual
- ⏳ Estudio de ahorro automatizado
- ⏳ Liquidación mensual

## MODELO LICENCIA SOLDELIA
- Compra: código + documentación + formación
- Mantenimiento anual
- SMS: coste propio del cliente
