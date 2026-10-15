# Revenue — Aparthotel Neptuno Costa Adeje

Dashboard de revenue management del Aparthotel Neptuno Costa Adeje
(Tenerife Sur, 95 unidades). Toma el Excel semanal de pickup/ADR que exporta el PMS, lo
acumula en un histórico y dibuja la evolución de ocupación, ADR, RevPAR y
pickup por ventana, con comparativa del año anterior.

## Uso semanal

**Desde cualquier sitio (MacBook, móvil, este PC):**

1. Abre la URL del dashboard.
2. Si lleva más de 12 h sin visitas estará dormido: pulsa el botón para
   despertarlo y espera ~30 s. Es normal en el plan gratuito de Streamlit.
3. Despliega **📥 Cargar el Excel del lunes**, suelta el `Planning de PickUpADR`
   y pulsa *Cargar al histórico*.

**Desde este PC, sin navegador (respaldo):** arrastra el Excel al acceso directo
*BUZON Neptuno* del escritorio y haz doble clic en *Finca*.

Los dos caminos hacen exactamente lo mismo y escriben en el mismo sitio. Cargar
dos veces el mismo Excel es inocuo: se deduplica por `(Snapshot, Fecha)`.

## Arquitectura

```
Navegador  ─┐
            ├─→  app.py  ─→  src/ingest/pipeline.py  ─→  Almacen
Buzón local ┘                                              ├─ AlmacenGitHub (nube)
                                                           └─ AlmacenLocal  (disco)
```

Hay **dos repositorios**, y la separación es deliberada:

| Repo | Visibilidad | Qué lleva |
|---|---|---|
| `revenue-neptuno` | **Pública** | Solo código. Ni un dato del hotel. |
| `revenue-neptuno-datos` | **Privada** | El histórico y los Excel semanales. |

Por qué separados: Streamlit Community Cloud **reinicia la app en cada push** al
repo desde el que publica. Si los datos vivieran ahí, cada carga de Excel
reiniciaría la app a media operación.

Por qué el código es público: para publicar desde un repo privado, Streamlit
exige un permiso de GitHub con lectura y escritura sobre *todos* los repos de la
cuenta. Con el código público ese permiso no hace falta. **El dashboard sigue
siendo privado**: su visibilidad se configura aparte, por lista de invitados.

## Puesta en marcha

### En la nube

1. Repos en GitHub: `revenue-neptuno` (pública) y `revenue-neptuno-datos` (privada).
2. Un *fine-grained token* con acceso **solo** a `revenue-neptuno-datos` y permiso
   `Contents: Read and write`.
3. Sube el código a la repo pública y los datos actuales a la privada,
   respetando las rutas `data/historico/historico_neptuno.xlsx` y `Excel-Lunes/`.
4. En [share.streamlit.io](https://share.streamlit.io): *New app* → repo
   `revenue-neptuno` → fichero `app.py`.
5. *Settings → Secrets*: pega el contenido de
   [.streamlit/secrets.toml.ejemplo](.streamlit/secrets.toml.ejemplo) con tu token.
6. *Settings → Sharing* → **"Only specific people can view this app"** y añade
   tu email. Sin este paso el dashboard queda abierto a quien tenga el enlace.

### En este PC

```bash
.venv/Scripts/pip install -r requirements.txt
```

Para que el buzón local escriba también en la nube, copia
`.streamlit/secrets.toml.ejemplo` a `.streamlit/secrets.toml` y pon el token.
Sin ese fichero todo funciona igual, pero contra el histórico local.

Arrancar a mano: `streamlit run app.py`

## Estructura

```
app.py                      Dashboard (lee del almacén, sube Excel, descarga histórico)
src/
  inventario.py             Fuente única del 17 y de la invariante R+L+Bloqueadas
  ingest/excel_reader.py    Validación del Excel del PMS (acepta ruta o bytes)
  ingest/pipeline.py        La ingesta de principio a fin (web y buzón comparten)
  storage/almacen.py        AlmacenLocal y AlmacenGitHub tras una misma interfaz
  storage/historico.py      Fusión y deduplicación (cálculo puro)
  analysis/series.py        KPIs y DataFrames. Sin I/O.
  ui/graficos.py            Las 9 figuras Plotly. Sin I/O.
  ui/tema.py                Paleta, plantilla Plotly y CSS
scripts/procesar_buzon.py   Respaldo local: recorre Excel-Lunes/BUZON
Neptuno.bat                   Doble clic en Windows: buzón + dashboard
docs/formato-excel.md       Esquema de las 149 columnas del PMS
```

Las decisiones de diseño y el porqué de cada una están en [CLAUDE.md](CLAUDE.md).

## Nota sobre `assets/`

`assets/logo.png` y `assets/hero_piscina.jpg` **sí se versionan** (el `.gitignore`
los exceptúa), porque `app.py` las incrusta en la cabecera y la barra lateral. Sin
ellas, la versión en la nube saldría sin logo. En el proyecto hermano
`revenue-finca` las imágenes se ignoran, porque allí no se usan.

## Avisos

- **Nunca** subas un Excel del hotel ni `secrets.toml` a la repo pública. El
  `.gitignore` lo impide (ignora `*.xlsx` en cualquier carpeta), pero conviene
  mirar `git status` antes de publicar.
- El histórico se puede descargar en Excel desde la barra lateral del dashboard.
- Si el histórico se corrompiera, se reconstruye entero volviendo a cargar los
  Excel semanales archivados en la repo de datos. Por eso se guardan.
