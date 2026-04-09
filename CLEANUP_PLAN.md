# Plan de limpieza segura

Auditoria: 2026-04-09

Este documento es una propuesta. No borrar datos operativos reales sin backup y
sin confirmar que dashboard, pipeline y WhatsApp no los estan usando.

## Evidencia principal

- Repo remoto: `git@github.com:dvdbrao-dev/mejoradora_leads.git`.
- Rama local auditada: `master`.
- Ultimo commit visto: `b7191de fix: manolo_model bug + surplus sanitize + auditor menos estricto + scraper_custom_zone`.
- Archivos versionados: 7.729.
- `whatsapp/node_modules/**` versionados: 7.131 archivos.
- `whatsapp/auth_info/**` versionados: 547 archivos.
- `runs/**` versionados: 1 archivo (`runs/enriched.json`).
- `inputs/**` versionados: 8 archivos.
- Artefactos operativos locales detectados: 1.095 JSON en `runs/`, 1.426 JSON
  en `outputs/analysis` + `outputs/messages`.
- Tamano local del repo auditado: aprox. 500 MB incluyendo `.git`.

## Limpieza propuesta del repo

### Borrar del indice git, conservar regenerable localmente si hace falta

- `whatsapp/node_modules/`
  - Evidencia: 7.131 archivos trackeados; las dependencias estan declaradas en
    `whatsapp/package.json` y `whatsapp/package-lock.json`.
- `whatsapp/auth_info/`
  - Evidencia: 547 archivos trackeados; contiene perfil/sesion/cache de navegador.
- `whatsapp/.wwebjs_cache/`
  - Evidencia: cache HTML de WhatsApp Web; no es codigo fuente.

Comando recomendado en una rama de limpieza, despues de commit de docs:

```bash
git rm -r --cached whatsapp/node_modules whatsapp/auth_info whatsapp/.wwebjs_cache
git status --short
```

### Mantener fuera del repo

- `inputs/raw/`: CSV/HTML de scraping.
- `inputs/cleaned/`: normalizaciones generadas.
- `runs/*.json`: resultados por lead. Excepciones posibles: `runs/enriched.json`,
  `runs/lead_status.json` si se decide versionarlos; la opcion mas limpia es
  mover indices operativos a `data/operational/` o a almacenamiento externo.
- `outputs/`: mensajes, analisis y CSV generados.
- `*.log`, `__pycache__/`, `*.pyc`.

### Mover a `legacy/` despues de un commit de archivo

- `BIBLE.md` -> `legacy/openfang/BIBLE.md`
- `STATE_OF_PROJECT.md` -> `legacy/openfang/STATE_OF_PROJECT.md`
- `phase_2.json` -> `legacy/openfang/phase_2.json`

No hacerlo en el mismo commit que arregle pipeline: son documentos historicos.

### Revisar antes de borrar

- `scripts/scraper.py`: puede ser duplicado parcial de `scraper_solar.py`, pero
  todavia es un scraper ejecutable.
- `scripts/cron_*.sh`: contienen rutas absolutas legacy; borrar solo si no hay
  cron/systemd que los llame.
- `scripts/export_mensajes.py`: no borrar hasta tener cola/contact queue nueva.

## Limpieza propuesta del VPS

Directorios/archivos observados en `/home/dvdbrao`:

- `/home/dvdbrao/openfang`: repo auditado.
- `/home/dvdbrao/openfang_nuevo`: esqueleto antiguo de aprox. 100 KB.
- `/home/dvdbrao/openfang.zip`: zip pequeno de aprox. 20 KB.
- `/home/dvdbrao/openclaw`: repo/plataforma distinta; aprox. 2.0 GB.
- `/home/dvdbrao/openclaw_*`, `/home/dvdbrao/openclaw-*`: backups, snapshots,
  logs y tarballs de otra etapa.
- `/home/dvdbrao/.openfang`: instalacion/plataforma distinta; no confundir con
  Mejoradora Leads.

Propuesta:

1. Crear un backup externo o snapshot del VPS.
2. Confirmar procesos activos con `ps`/systemd/cron antes de mover nada.
3. Archivar fuera del home los tarballs `openclaw*.tgz` que se quieran conservar.
4. Mover `/home/dvdbrao/openfang_nuevo` a una carpeta de archivo o borrarlo si
   ya esta en git/backups.
5. No tocar `/home/dvdbrao/openclaw` ni `~/.openclaw*` en la misma operacion que
   Mejoradora Leads; es grande, pero es otro sistema.
6. No borrar `runs/`, `outputs/` ni `whatsapp/auth_info/` del VPS hasta saber si
   hacen falta para dashboard, auditoria comercial o reconexion WhatsApp.

## Riesgos antes de limpieza real

- `whatsapp/auth_info/` puede ser la sesion WhatsApp activa. Sacarla de git no
  la borra localmente, pero borrarla del VPS obligaria a reautenticar.
- `runs/` mezcla resultados de lead con JSON auxiliares. Todo agregador debe
  validar que lee dicts de run, no listas/indices.
- El dashboard lee `runs/` y `data/plants.json`; si se mueven runs hay que
  configurar su nueva ubicacion.
- `scripts/enrich.py`, `scripts/enrich_web.py`, `whatsapp/send.py` y algunos
  cron usan rutas absolutas o `~/openfang`.
- `whatsapp/send.py` esta en piloto; cambiar `TEST_MODE` sin proceso de
  aprobacion puede enviar mensajes reales.

## Nota de ejecucion

Actualizado: 2026-04-09

### Ya limpiado del indice

- `whatsapp/node_modules/`
- `whatsapp/auth_info/`
- `whatsapp/.wwebjs_cache/`

La limpieza se hizo con `git rm -r --cached`, asi que los archivos siguen
presentes en disco local y no se ha roto la sesion ni el runtime por borrado
fisico.

### Sigue pendiente

- Confirmar e introducir los cambios en git con un commit de limpieza.
- Medir el tamano del repo tras reescritura normal del arbol de trabajo y, si
  hace falta, revisar historial mas adelante. Esta iteracion no toca historial.
- Decidir el destino de `BIBLE.md`, `STATE_OF_PROJECT.md` y `phase_2.json`
  dentro de `legacy/`.
- Revisar si `runs/enriched.json` y `runs/lead_status.json` deben seguir
  versionados o pasar tambien a runtime local.

### No tocar todavia

- Migracion fisica de `/home/dvdbrao/openfang` a otra carpeta.
- Logica del pipeline en `scripts/`.
- `runs/`, `outputs/` y `inputs/raw/` del VPS si pueden hacer falta para
  dashboard, trazabilidad o auditoria.
- Borrado local de `whatsapp/auth_info/` hasta confirmar si la sesion actual se
  necesita.
