"""
Conector con Obsidian para el Asistente Persistente.

Permite:
- Localizar o inicializar una bóveda (Vault) de Obsidian con estructura organizada.
- Crear y leer notas diarias (Daily Notes) en formato YYYY-MM-DD.md.
- Listar, agregar y marcar tareas con sintaxis Markdown `- [ ]` y `- [x]`.
- Guardar notas de captura rápida en 📥 Captura_Rapida/.
- Buscar información o tareas pendientes en todo el Vault.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DIAS_SEMANA_ES = [
    "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"
]


class ConectorObsidian:
    """Administra la lectura y escritura dentro de la bóveda de Obsidian."""

    def __init__(self, ruta_vault: Optional[str | Path] = None):
        if ruta_vault:
            self.ruta_vault = Path(ruta_vault).expanduser().resolve()
        else:
            # 1. Buscar en variable de entorno
            env_path = os.getenv("OBSIDIAN_VAULT_PATH")
            if env_path:
                self.ruta_vault = Path(env_path).expanduser().resolve()
            else:
                # 2. Intentar autodetectar el Vault activo real configurado en Obsidian
                vault_autodetectado = self._autodetectar_vault_obsidian()
                if vault_autodetectado:
                    self.ruta_vault = vault_autodetectado
                else:
                    # 3. Bóveda por defecto dentro de Documentos o localmente
                    docs = Path.home() / "Documents" / "ObsidianVault"
                    self.ruta_vault = docs if docs.parent.exists() else (Path.cwd() / "obsidian_vault").resolve()

        # Carpetas estándar de la estructura (nombres de carpetas seguros para cualquier SO)
        self.dir_diario = self.ruta_vault / "Diario"
        self.dir_tareas = self.ruta_vault / "Tareas"
        self.dir_proyectos = self.ruta_vault / "Proyectos"
        self.dir_captura = self.ruta_vault / "Capturas"

        self._asegurar_estructura()

    @staticmethod
    def _autodetectar_vault_obsidian() -> Optional[Path]:
        """Detecta la ruta de la bóveda de Obsidian actualmente abierta o configurada en el sistema."""
        try:
            import json
            config_paths = [
                Path.home() / "AppData" / "Roaming" / "obsidian" / "obsidian.json",
                Path.home() / ".config" / "obsidian" / "obsidian.json",
            ]
            for cfg in config_paths:
                if cfg.exists():
                    data = json.loads(cfg.read_text(encoding="utf-8"))
                    vaults = data.get("vaults", {})
                    # Buscar el vault con "open": true
                    for v_id, v_info in vaults.items():
                        if v_info.get("open") is True and "path" in v_info:
                            p = Path(v_info["path"])
                            if p.exists():
                                return p.resolve()
                    # Si ninguno tiene open=true, tomar el primero que exista
                    for v_id, v_info in vaults.items():
                        if "path" in v_info:
                            p = Path(v_info["path"])
                            if p.exists():
                                return p.resolve()
        except Exception:
            pass
        return None

    def _asegurar_estructura(self) -> None:
        """Crea las carpetas y archivos base del Vault si no existen."""
        for carpeta in [self.dir_diario, self.dir_tareas, self.dir_proyectos, self.dir_captura]:
            carpeta.mkdir(parents=True, exist_ok=True)

        archivo_pendientes = self.dir_tareas / "Pendientes_Generales.md"
        if not archivo_pendientes.exists():
            archivo_pendientes.write_text(
                "# 📌 Tareas y Pendientes Generales\n\n"
                "- [ ] Configurar mi Asistente Persistente\n"
                "- [ ] Definir proyectos prioritarios del mes\n",
                encoding="utf-8"
            )

    @staticmethod
    def _formatear_fecha(fecha: Optional[date | datetime | str] = None) -> tuple[str, str]:
        """Devuelve (YYYY-MM-DD, NombreDiaSemana) para una fecha dada."""
        if fecha is None:
            obj_fecha = date.today()
        elif isinstance(fecha, datetime):
            obj_fecha = fecha.date()
        elif isinstance(fecha, date):
            obj_fecha = fecha
        else:
            try:
                obj_fecha = datetime.strptime(str(fecha), "%Y-%m-%d").date()
            except ValueError:
                obj_fecha = date.today()

        nombre_dia = DIAS_SEMANA_ES[obj_fecha.weekday()]
        return obj_fecha.strftime("%Y-%m-%d"), nombre_dia

    def obtener_ruta_nota_diaria(self, fecha: Optional[date | datetime | str] = None) -> Path:
        """Devuelve la ruta a la nota diaria correspondiente a la fecha."""
        fecha_str, _ = self._formatear_fecha(fecha)
        return self.dir_diario / f"{fecha_str}.md"

    def obtener_o_crear_nota_diaria(self, fecha: Optional[date | datetime | str] = None) -> Path:
        """Obtiene la ruta de la nota diaria; si no existe, la crea con plantilla limpia."""
        fecha_str, nombre_dia = self._formatear_fecha(fecha)
        ruta_nota = self.obtener_ruta_nota_diaria(fecha)

        if not ruta_nota.exists():
            contenido_inicial = (
                f"# 📅 {fecha_str} - {nombre_dia}\n\n"
                "## 🎯 Objetivos y Citas del Día\n"
                "- Sin eventos registrados aún.\n\n"
                "## ✅ Tareas Pendientes\n\n"
                "## 📝 Notas Rápidas y Bitácora\n\n"
            )
            ruta_nota.write_text(contenido_inicial, encoding="utf-8")

        return ruta_nota

    def leer_nota_diaria(self, fecha: Optional[date | datetime | str] = None) -> Dict[str, Any]:
        """
        Lee y estructura el contenido de una nota diaria.
        Retorna tareas pendientes, tareas completadas, citas y contenido general.
        """
        ruta_nota = self.obtener_o_crear_nota_diaria(fecha)
        contenido = ruta_nota.read_text(encoding="utf-8")
        fecha_str, nombre_dia = self._formatear_fecha(fecha)

        tareas_pendientes: List[str] = []
        tareas_completadas: List[str] = []

        lineas = contenido.splitlines()
        for linea in lineas:
            linea_strip = linea.strip()
            if linea_strip.startswith("- [ ] "):
                tareas_pendientes.append(linea_strip[6:].strip())
            elif linea_strip.startswith("- [x] ") or linea_strip.startswith("- [X] "):
                tareas_completadas.append(linea_strip[6:].strip())

        return {
            "fecha": fecha_str,
            "dia": nombre_dia,
            "ruta": str(ruta_nota),
            "tareas_pendientes": tareas_pendientes,
            "tareas_completadas": tareas_completadas,
            "contenido_completo": contenido
        }

    def agregar_tarea_nota_diaria(self, tarea: str, fecha: Optional[date | datetime | str] = None) -> bool:
        """Agrega una nueva tarea en formato '- [ ] <tarea>' en la sección de tareas."""
        ruta_nota = self.obtener_o_crear_nota_diaria(fecha)
        contenido = ruta_nota.read_text(encoding="utf-8")

        nueva_linea = f"- [ ] {tarea.strip()}"

        # Buscar si ya existe la sección de tareas
        if "## ✅ Tareas Pendientes" in contenido:
            partes = contenido.split("## ✅ Tareas Pendientes", 1)
            # Insertar justo después del encabezado
            resto = partes[1]
            contenido_actualizado = f"{partes[0]}## ✅ Tareas Pendientes\n{nueva_linea}\n{resto.lstrip()}"
        else:
            contenido_actualizado = f"{contenido.strip()}\n\n## ✅ Tareas Pendientes\n{nueva_linea}\n"

        ruta_nota.write_text(contenido_actualizado, encoding="utf-8")
        return True

    def marcar_tarea(self, texto_tarea: str, completada: bool = True, fecha: Optional[date | datetime | str] = None) -> bool:
        """Marca una tarea como completada [x] o pendiente [ ] buscando por coincidencia de texto."""
        ruta_nota = self.obtener_o_crear_nota_diaria(fecha)
        contenido = ruta_nota.read_text(encoding="utf-8")

        origen = "- [ ]" if completada else "- [x]"
        destino = "- [x]" if completada else "- [ ]"

        lineas = contenido.splitlines()
        modificado = False
        nuevas_lineas = []

        for linea in lineas:
            if not modificado and texto_tarea.lower() in linea.lower():
                if origen in linea:
                    linea = linea.replace(origen, destino, 1)
                    modificado = True
                elif not completada and "- [X]" in linea:
                    linea = linea.replace("- [X]", destino, 1)
                    modificado = True
            nuevas_lineas.append(linea)

        if modificado:
            ruta_nota.write_text("\n".join(nuevas_lineas) + "\n", encoding="utf-8")
            return True
        return False

    def agregar_captura_rapida(self, texto: str, titulo: Optional[str] = None) -> Path:
        """Guarda un pensamiento o nota rápida en la carpeta 📥 Captura_Rapida/."""
        ahora = datetime.now()
        timestamp = ahora.strftime("%Y-%m-%d_%H%M%S")
        if not titulo:
            # Tomar primeras 4 palabras como nombre seguro
            palabras = re.sub(r'[^a-zA-Z0-9_\sáéíóúÁÉÍÓÚñÑ]', '', texto).split()[:4]
            titulo = "_".join(palabras) if palabras else "Captura"

        nombre_archivo = f"{timestamp}_{titulo[:30]}.md"
        ruta_archivo = self.dir_captura / nombre_archivo

        contenido = (
            f"# 📥 {titulo}\n\n"
            f"> Fecha de captura: {ahora.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"{texto.strip()}\n"
        )
        ruta_archivo.write_text(contenido, encoding="utf-8")
        return ruta_archivo

    def agregar_bitacora(self, texto: str, fecha: Optional[date | datetime | str] = None) -> bool:
        """Agrega un apunte con marca de tiempo en la sección de Bitácora de la nota diaria."""
        ruta_nota = self.obtener_o_crear_nota_diaria(fecha)
        contenido = ruta_nota.read_text(encoding="utf-8")
        hora_str = datetime.now().strftime("%H:%M")
        linea_apunte = f"- **{hora_str}:** {texto.strip()}"

        if "## 📝 Notas Rápidas y Bitácora" in contenido:
            contenido_actualizado = f"{contenido.rstrip()}\n{linea_apunte}\n"
        else:
            contenido_actualizado = f"{contenido.rstrip()}\n\n## 📝 Notas Rápidas y Bitácora\n{linea_apunte}\n"

        ruta_nota.write_text(contenido_actualizado, encoding="utf-8")
        return True

    def listar_todas_las_tareas_pendientes(self) -> List[Dict[str, Any]]:
        """Recorre las notas diarias y la lista general para extraer todas las tareas pendientes."""
        tareas: List[Dict[str, Any]] = []

        # 1. Revisar notas diarias recientes (últimos 14 días)
        if self.dir_diario.exists():
            archivos_diario = sorted(self.dir_diario.glob("*.md"), reverse=True)[:14]
            for archivo in archivos_diario:
                fecha_nombre = archivo.stem
                try:
                    contenido = archivo.read_text(encoding="utf-8")
                    for linea in contenido.splitlines():
                        if linea.strip().startswith("- [ ] "):
                            tareas.append({
                                "tarea": linea.strip()[6:].strip(),
                                "origen": f"Diario ({fecha_nombre})",
                                "archivo": str(archivo),
                                "completada": False
                            })
                except Exception:
                    continue

        # 2. Revisar pendientes generales
        archivo_pendientes = self.dir_tareas / "Pendientes_Generales.md"
        if archivo_pendientes.exists():
            try:
                contenido = archivo_pendientes.read_text(encoding="utf-8")
                for linea in contenido.splitlines():
                    if linea.strip().startswith("- [ ] "):
                        tareas.append({
                            "tarea": linea.strip()[6:].strip(),
                            "origen": "Tareas Generales",
                            "archivo": str(archivo_pendientes),
                            "completada": False
                        })
            except Exception:
                pass

        return tareas
