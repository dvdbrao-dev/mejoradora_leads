# Roadmap

Estado: 2026-04-09

## Norte

Cerrar la arquitectura real del proyecto antes de tocar logica de negocio:

- repo pequeno y limpio
- separacion clara entre fuente de verdad y runtime
- modelo de dominio comun
- estados operativos coherentes
- ruta legacy contenida

## Bloque actual

1. Arquitectura y reglas
   - fijar documentos oficiales
   - fijar politica repo vs runtime
   - fijar entidades y estados oficiales
   - decidir el tratamiento de `STATE_OF_PROJECT.md`

2. Higiene de repo
   - mantener runtime fuera del indice
   - evitar nuevos hardcodes `openfang`
   - asegurar que docs y `.gitignore` mandan sobre la estructura

3. Reproducibilidad minima
   - `requirements.txt` alineado con imports reales
   - `whatsapp/package*.json` como unica fuente de dependencias Node
   - comandos de validacion simples y repetibles

## Siguiente bloque recomendado

1. Configuracion y paths
   - introducir una variable de entorno o helper comun para la ruta base del
     proyecto
   - reemplazar hardcodes `~/openfang` sin cambiar logica de negocio
   - mantener compatibilidad con la ruta legacy actual

2. Estado operativo
   - separar lectores de runs de indices auxiliares
   - decidir destino futuro de `runs/enriched.json` y `runs/lead_status.json`
   - preparar `runtime/state/` o equivalente sin mover datos todavia

3. Contact queue
   - definir contrato de `ContactQueue`
   - corregir la salida comercial sin tocar el core del pipeline
   - dejar trazabilidad de contacto y resultado

## Despues

1. Migrar docs legacy a `legacy/openfang/`
2. Crear fixtures de test pequenos y representativos
3. Renombrar titulo interno del dashboard a Mejoradora Leads
4. Preparar la migracion fisica de carpeta cuando los paths ya no dependan de
   `openfang`

## Fuera de alcance en esta fase

- refactor grande de `scripts/route.py`
- cambios de prompts/agentes por estrategia comercial
- automatizaciones nuevas de envio
- migracion fisica de `/home/dvdbrao/openfang`
- borrado irreversible de datos operativos del VPS
