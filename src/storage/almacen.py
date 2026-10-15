"""Dónde viven el histórico y los Excel archivados.

Dos implementaciones con la misma interfaz, para que el mismo código corra en
la nube y en este PC:

- `AlmacenLocal`  — ficheros en disco. Es el comportamiento de siempre y el
  respaldo cuando no hay internet.
- `AlmacenGitHub` — un repositorio privado de GitHub. Cada carga queda como un
  commit, así que el histórico tiene copia de seguridad versionada gratis.

`crear_almacen()` elige uno u otro según haya credenciales configuradas.
"""
from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

HOJA_HISTORICO = "Historico"
RUTA_HISTORICO = "data/historico/historico_neptuno.xlsx"
CARPETA_ARCHIVO = "Excel-Lunes"
CABECERA_CADUCIDAD = "GitHub-Authentication-Token-Expiration"

MESES_LARGOS_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre",
    11: "Noviembre", 12: "Diciembre",
}


class ErrorAlmacen(Exception):
    """Fallo al leer o escribir en el almacén (red, permisos, token...)."""


def carpeta_destino(snapshot) -> str:
    """`Excel-Lunes/2026-09-Septiembre/Semana-38_2026-09-15`.

    El nombre sale de la fecha del SNAPSHOT (el contenido del Excel), no del
    reloj del sistema: así archiva en el sitio correcto aunque se procese con
    retraso, y da igual la zona horaria del servidor.
    """
    fecha = snapshot.date() if hasattr(snapshot, "date") else snapshot
    mes = f"{fecha.year}-{fecha.month:02d}-{MESES_LARGOS_ES[fecha.month]}"
    semana = f"Semana-{fecha.isocalendar().week:02d}_{fecha.isoformat()}"
    return f"{CARPETA_ARCHIVO}/{mes}/{semana}"


def historico_a_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=HOJA_HISTORICO, index=False)
    return buf.getvalue()


# ─────────────────────────── Interfaz ───────────────────────────

class Almacen(ABC):
    @abstractmethod
    def leer_historico(self) -> pd.DataFrame | None:
        """El histórico acumulado, o None si todavía no existe."""

    @abstractmethod
    def escribir_historico(self, df: pd.DataFrame, mensaje: str) -> None: ...

    @abstractmethod
    def archivar_excel(self, nombre: str, datos: bytes, snapshot) -> str:
        """Guarda el Excel original. Devuelve dónde quedó."""

    @abstractmethod
    def descripcion(self) -> str:
        """Texto corto para mostrar en la barra lateral."""

    @abstractmethod
    def version(self) -> str:
        """Identificador del estado actual del histórico.

        Sirve de clave de caché: si cambia, hay que releer. En local es la
        fecha de modificación; en GitHub, el sha del fichero.
        """

    def dias_hasta_caducidad(self) -> int | None:
        """Días que le quedan a la credencial, o None si no caduca o no se sabe.

        El almacén local no usa credenciales, así que nunca caduca.
        """
        return None

    def historico_bytes(self) -> bytes | None:
        """El histórico tal cual, para el botón de descarga."""
        df = self.leer_historico()
        return None if df is None else historico_a_bytes(df)


# ─────────────────────────── Local ───────────────────────────

class AlmacenLocal(Almacen):
    def __init__(self, raiz: Path):
        self.raiz = Path(raiz)
        self.ruta_historico = self.raiz / RUTA_HISTORICO

    def leer_historico(self) -> pd.DataFrame | None:
        if not self.ruta_historico.exists():
            return None
        return pd.read_excel(self.ruta_historico, sheet_name=HOJA_HISTORICO)

    def escribir_historico(self, df: pd.DataFrame, mensaje: str) -> None:
        self.ruta_historico.parent.mkdir(parents=True, exist_ok=True)
        # Escritura atómica: si el proceso muere a media escritura, el
        # histórico anterior sigue intacto. Antes se truncaba el fichero
        # bueno antes de tener el nuevo, y no hay copia de seguridad.
        temporal = self.ruta_historico.with_suffix(".tmp.xlsx")
        temporal.write_bytes(historico_a_bytes(df))
        temporal.replace(self.ruta_historico)

    def archivar_excel(self, nombre: str, datos: bytes, snapshot) -> str:
        destino_dir = self.raiz / carpeta_destino(snapshot)
        destino_dir.mkdir(parents=True, exist_ok=True)
        destino = destino_dir / nombre
        destino.write_bytes(datos)
        return str(destino.relative_to(self.raiz))

    def descripcion(self) -> str:
        return f"Local · `{RUTA_HISTORICO}`"

    def version(self) -> str:
        if not self.ruta_historico.exists():
            return "vacio"
        return str(self.ruta_historico.stat().st_mtime)


# ─────────────────────────── GitHub ───────────────────────────

class AlmacenGitHub(Almacen):
    """Repositorio privado de GitHub como almacén.

    OJO: debe ser un repo DISTINTO del que publica la app. Streamlit Community
    Cloud reinicia la app en cada push al repo desde el que despliega, así que
    si los datos vivieran ahí, cada carga de Excel reiniciaría la app a media
    operación.
    """

    API = "https://api.github.com"

    def __init__(self, repo: str, token: str, rama: str = "main"):
        self.repo = repo
        self.rama = rama
        self._cabeceras = {
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._caduca: datetime | None = None

    def _url(self, ruta: str) -> str:
        return f"{self.API}/repos/{self.repo}/contents/{ruta}"

    def _descargar(self, ruta: str) -> bytes | None:
        """Contenido crudo de un fichero, o None si no existe.

        `Accept: application/vnd.github.raw` es imprescindible: el formato JSON
        por defecto devuelve el contenido VACÍO para ficheros de más de 1 MB,
        sin dar error. El histórico ya pesa 1,76 MB.
        """
        r = self._peticion(
            requests.get, self._url(ruta), f"leer {ruta}",
            headers={**self._cabeceras, "Accept": "application/vnd.github.raw"},
            params={"ref": self.rama}, timeout=60,
        )
        if r.status_code == 404:
            return None
        self._comprobar(r, f"leer {ruta}")
        return r.content

    def _sha(self, ruta: str) -> str | None:
        """Sha del fichero, necesario para sobrescribirlo. None si no existe."""
        r = self._peticion(
            requests.get, self._url(ruta), f"consultar {ruta}",
            headers={**self._cabeceras, "Accept": "application/vnd.github.object"},
            params={"ref": self.rama}, timeout=30,
        )
        if r.status_code == 404:
            return None
        self._comprobar(r, f"consultar {ruta}")
        return r.json().get("sha")

    def _subir(self, ruta: str, datos: bytes, mensaje: str, sha: str | None) -> None:
        cuerpo = {
            "message": mensaje,
            "content": base64.b64encode(datos).decode("ascii"),
            "branch": self.rama,
        }
        if sha:
            cuerpo["sha"] = sha
        r = self._peticion(requests.put, self._url(ruta), f"escribir {ruta}",
                           headers=self._cabeceras, json=cuerpo, timeout=120)
        self._comprobar(r, f"escribir {ruta}")

    def _peticion(self, metodo, url, accion, **kw):
        """Llama a GitHub traduciendo los fallos de red a `ErrorAlmacen`.

        Sin esto, quedarse sin internet revienta con una excepcion de
        `requests` que la interfaz no espera y acaba en un error feo de Python
        en pantalla, en vez de un mensaje que se entienda.
        """
        try:
            r = metodo(url, **kw)
            self._anotar_caducidad(r)
            return r
        except requests.exceptions.Timeout:
            raise ErrorAlmacen(
                f"GitHub no responde al {accion}. Puede ser lentitud puntual: "
                f"vuelve a intentarlo en un minuto."
            ) from None
        except requests.exceptions.ConnectionError:
            raise ErrorAlmacen(
                f"Sin conexion con GitHub al {accion}. Revisa tu internet. "
                f"Los datos en la nube no se han tocado."
            ) from None
        except requests.exceptions.RequestException as e:
            raise ErrorAlmacen(f"Fallo de red al {accion}: {e}") from None

    @staticmethod
    def _comprobar(r: requests.Response, accion: str) -> None:
        if r.ok:
            return
        if r.status_code == 401:
            raise ErrorAlmacen(
                f"GitHub rechaza el token al {accion}. Revisa que no haya caducado."
            )
        if r.status_code == 403:
            raise ErrorAlmacen(
                f"Sin permiso para {accion}. El token necesita "
                f"Contents: Read and write sobre el repo de datos."
            )
        if r.status_code == 404:
            raise ErrorAlmacen(
                f"No se encuentra el repo al {accion}. Revisa el nombre "
                f"(formato `usuario/repo`) y que el token lo incluya."
            )
        raise ErrorAlmacen(f"GitHub devolvio {r.status_code} al {accion}: {r.text[:200]}")

    def _anotar_caducidad(self, r) -> None:
        """Guarda cuándo caduca el token, que GitHub manda en cada respuesta."""
        valor = r.headers.get(CABECERA_CADUCIDAD)
        if not valor:
            return
        try:
            t = datetime.strptime(valor.replace(" UTC", "").strip(),
                                  "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return
        # GitHub tiene un fallo conocido por el que a veces manda la hora
        # actual del servidor en lugar de la caducidad real. Una fecha pegada
        # a ahora es mucho mas probable que sea ese fallo que un token que
        # caduca en este mismo minuto, asi que se descarta en vez de dar un
        # aviso falso. Si de verdad hubiera caducado, GitHub responderia 401 y
        # ya se avisa por otro lado.
        if t - datetime.now(timezone.utc) < timedelta(minutes=5):
            return
        self._caduca = t

    def dias_hasta_caducidad(self) -> int | None:
        if self._caduca is None:
            return None
        return (self._caduca - datetime.now(timezone.utc)).days

    def leer_historico(self) -> pd.DataFrame | None:
        datos = self._descargar(RUTA_HISTORICO)
        if datos is None:
            return None
        if not datos:
            # Defensa explicita contra el fallo del limite de 1 MB: si alguna
            # vez llega vacio, es mejor romper que creer que no hay historico
            # y sobrescribirlo con un solo snapshot.
            raise ErrorAlmacen(
                "El historico llego vacio desde GitHub. No se continua para no "
                "sobrescribir los datos existentes."
            )
        return pd.read_excel(BytesIO(datos), sheet_name=HOJA_HISTORICO)

    def escribir_historico(self, df: pd.DataFrame, mensaje: str) -> None:
        self._subir(RUTA_HISTORICO, historico_a_bytes(df), mensaje,
                    self._sha(RUTA_HISTORICO))

    def archivar_excel(self, nombre: str, datos: bytes, snapshot) -> str:
        ruta = f"{carpeta_destino(snapshot)}/{nombre}"
        self._subir(ruta, datos, f"Archiva {nombre}", self._sha(ruta))
        return ruta

    def descripcion(self) -> str:
        return f"Nube · `{self.repo}`"

    def version(self) -> str:
        return self._sha(RUTA_HISTORICO) or "vacio"


# ─────────────────────────── Selección ───────────────────────────

def _credenciales() -> dict | None:
    """Credenciales de GitHub desde st.secrets o variables de entorno."""
    try:
        import streamlit as st
        if "github" in st.secrets:
            cfg = st.secrets["github"]
            return {"repo": cfg["repo"], "token": cfg["token"],
                    "rama": cfg.get("rama", "main")}
    except Exception:
        # Sin Streamlit, sin secrets.toml o sin la seccion [github]: se cae a
        # las variables de entorno y, si tampoco, a local.
        pass

    repo, token = os.environ.get("FINCA_REPO_DATOS"), os.environ.get("FINCA_TOKEN")
    if repo and token:
        return {"repo": repo, "token": token,
                "rama": os.environ.get("FINCA_RAMA", "main")}
    return None


def crear_almacen(raiz: Path | None = None) -> Almacen:
    """El almacén de la nube si hay credenciales; si no, el local."""
    cred = _credenciales()
    if cred:
        return AlmacenGitHub(**cred)
    return AlmacenLocal(raiz or Path(__file__).resolve().parents[2])
