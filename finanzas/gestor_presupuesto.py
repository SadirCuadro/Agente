"""
Módulo de gestión de presupuesto, categorización, transacciones y alertas financieras.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CATEGORIAS_PREDETERMINADAS = [
    "Alimentación",
    "Servicios Públicos",
    "Transporte",
    "Vivienda",
    "Salud",
    "Restaurantes & Ocio",
    "Suscripciones & Tecnología",
    "Educación",
    "Ropa & Cuidado Personal",
    "Otros",
]


@dataclass
class Gasto:
    """Modela una transacción o gasto registrado."""

    id: str = field(default_factory=lambda: f"GST-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}")
    fecha: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    comercio: str = "Comercio General"
    categoria: str = "Otros"
    monto: float = 0.0
    moneda: str = "COP"
    metodo_pago: str = "Tarjeta de Crédito"
    descripcion: str = ""
    tipo_documento: str = "Factura"
    confianza_extraccion: float = 1.0
    items: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "fecha": self.fecha,
            "comercio": self.comercio,
            "categoria": self.categoria,
            "monto": float(self.monto),
            "moneda": self.moneda,
            "metodo_pago": self.metodo_pago,
            "descripcion": self.descripcion,
            "tipo_documento": self.tipo_documento,
            "confianza_extraccion": float(self.confianza_extraccion),
            "items": self.items,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Gasto:
        return cls(
            id=data.get("id", f"GST-{uuid.uuid4().hex[:6].upper()}"),
            fecha=data.get("fecha", datetime.now().strftime("%Y-%m-%d")),
            comercio=data.get("comercio", "Comercio Desconocido"),
            categoria=data.get("categoria", "Otros"),
            monto=float(data.get("monto", 0.0)),
            moneda=data.get("moneda", "COP"),
            metodo_pago=data.get("metodo_pago", "Tarjeta de Crédito"),
            descripcion=data.get("descripcion", ""),
            tipo_documento=data.get("tipo_documento", "Factura"),
            confianza_extraccion=float(data.get("confianza_extraccion", 1.0)),
            items=data.get("items", []),
        )


@dataclass
class PresupuestoConfig:
    """Configuración de límites de gasto y umbrales de alerta."""

    presupuesto_total_mensual: float = 2500000.0
    presupuestos_por_categoria: Dict[str, float] = field(
        default_factory=lambda: {
            "Alimentación": 800000.0,
            "Servicios Públicos": 350000.0,
            "Transporte": 300000.0,
            "Vivienda": 600000.0,
            "Salud": 150000.0,
            "Restaurantes & Ocio": 250000.0,
            "Suscripciones & Tecnología": 100000.0,
            "Educación": 150000.0,
            "Otros": 100000.0,
        }
    )
    umbral_amarillo: float = 0.70  # Alerta preventiva al 70%
    umbral_rojo: float = 0.90      # Alerta crítica al 90%

    def to_dict(self) -> Dict[str, Any]:
        return {
            "presupuesto_total_mensual": self.presupuesto_total_mensual,
            "presupuestos_por_categoria": self.presupuestos_por_categoria,
            "umbral_amarillo": self.umbral_amarillo,
            "umbral_rojo": self.umbral_rojo,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PresupuestoConfig:
        return cls(
            presupuesto_total_mensual=float(data.get("presupuesto_total_mensual", 2500000.0)),
            presupuestos_por_categoria=data.get(
                "presupuestos_por_categoria",
                {
                    "Alimentación": 800000.0,
                    "Servicios Públicos": 350000.0,
                    "Transporte": 300000.0,
                    "Vivienda": 600000.0,
                    "Salud": 150000.0,
                    "Restaurantes & Ocio": 250000.0,
                    "Suscripciones & Tecnología": 100000.0,
                    "Educación": 150000.0,
                    "Otros": 100000.0,
                },
            ),
            umbral_amarillo=float(data.get("umbral_amarillo", 0.70)),
            umbral_rojo=float(data.get("umbral_rojo", 0.90)),
        )


class GestorPresupuesto:
    """Controlador central para persistencia y cálculo analítico de gastos."""

    def __init__(
        self,
        ruta_gastos: Optional[str | Path] = None,
        ruta_config: Optional[str | Path] = None,
    ):
        self.ruta_gastos = Path(ruta_gastos) if ruta_gastos else Path("data") / "gastos.json"
        self.ruta_config = Path(ruta_config) if ruta_config else Path("data") / "presupuesto_config.json"
        self._asegurar_archivos()

    def _asegurar_archivos(self) -> None:
        self.ruta_gastos.parent.mkdir(parents=True, exist_ok=True)
        if not self.ruta_gastos.exists():
            with open(self.ruta_gastos, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)

        if not self.ruta_config.exists():
            config_default = PresupuestoConfig()
            with open(self.ruta_config, "w", encoding="utf-8") as f:
                json.dump(config_default.to_dict(), f, indent=2, ensure_ascii=False)

    def cargar_config(self) -> PresupuestoConfig:
        try:
            with open(self.ruta_config, "r", encoding="utf-8") as f:
                data = json.load(f)
                return PresupuestoConfig.from_dict(data)
        except Exception:
            return PresupuestoConfig()

    def guardar_config(self, config: PresupuestoConfig) -> None:
        self.ruta_config.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ruta_config, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

    def cargar_gastos(self) -> List[Gasto]:
        self._asegurar_archivos()
        try:
            with open(self.ruta_gastos, "r", encoding="utf-8") as f:
                contenido = f.read().strip()
                if not contenido:
                    return []
                data = json.loads(contenido)
                return [Gasto.from_dict(item) for item in data]
        except Exception:
            return []

    def guardar_gastos(self, lista_gastos: List[Gasto]) -> None:
        self._asegurar_archivos()
        tmp = self.ruta_gastos.with_suffix(".tmp")
        data = [g.to_dict() for g in lista_gastos]
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.ruta_gastos)

    def agregar_gasto(self, gasto: Gasto) -> Gasto:
        gastos = self.cargar_gastos()
        gastos.insert(0, gasto)  # Insertar al inicio para ver las más recientes primero
        self.guardar_gastos(gastos)
        return gasto

    def eliminar_gasto(self, gasto_id: str) -> bool:
        gastos = self.cargar_gastos()
        nuevos = [g for g in gastos if g.id != gasto_id]
        if len(nuevos) != len(gastos):
            self.guardar_gastos(nuevos)
            return True
        return False

    def obtener_categorias(self) -> List[str]:
        return CATEGORIAS_PREDETERMINADAS

    def calcular_metricas(
        self,
        mes: Optional[int] = None,
        anio: Optional[int] = None,
        categoria_filtro: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calcula el balance consolidado, distribución, alertas y KPIs."""
        gastos = self.cargar_gastos()
        config = self.cargar_config()

        # Filtrar por fecha si se especifica
        ahora = datetime.now()
        mes_filtro = mes or ahora.month
        anio_filtro = anio or ahora.year

        gastos_filtrados: List[Gasto] = []
        for g in gastos:
            try:
                dt = datetime.strptime(g.fecha[:10], "%Y-%m-%d")
                if dt.year == anio_filtro and dt.month == mes_filtro:
                    if categoria_filtro and categoria_filtro != "Todas":
                        if g.categoria == categoria_filtro:
                            gastos_filtrados.append(g)
                    else:
                        gastos_filtrados.append(g)
            except ValueError:
                gastos_filtrados.append(g)

        total_gastado = sum(g.monto for g in gastos_filtrados)
        presupuesto_total = config.presupuesto_total_mensual
        restante = presupuesto_total - total_gastado
        porcentaje_consumido = round((total_gastado / presupuesto_total) * 100.0, 1) if presupuesto_total > 0 else 0.0

        # Estado del presupuesto global
        if porcentaje_consumido >= (config.umbral_rojo * 100.0):
            estado_global = "PELIGRO / CRÍTICO"
            color_estado = "red"
        elif porcentaje_consumido >= (config.umbral_amarillo * 100.0):
            estado_global = "ADVERTENCIA"
            color_estado = "orange"
        else:
            estado_global = "SALUDABLE"
            color_estado = "green"

        # Agrupación por categoría
        por_categoria: Dict[str, float] = {}
        for g in gastos_filtrados:
            por_categoria[g.categoria] = por_categoria.get(g.categoria, 0.0) + g.monto

        # Alertas específicas por categoría
        alertas_categoria: List[Dict[str, Any]] = []
        for cat, gastado_cat in por_categoria.items():
            limite_cat = config.presupuestos_por_categoria.get(cat, 0.0)
            if limite_cat > 0:
                pct = (gastado_cat / limite_cat) * 100.0
                if pct >= 100.0:
                    alertas_categoria.append({
                        "categoria": cat,
                        "gastado": gastado_cat,
                        "limite": limite_cat,
                        "porcentaje": round(pct, 1),
                        "nivel": "CRÍTICO",
                        "mensaje": f"Has superado el 100% del presupuesto asignado a {cat} (${gastado_cat:,.0f} de ${limite_cat:,.0f}).",
                    })
                elif pct >= (config.umbral_amarillo * 100.0):
                    alertas_categoria.append({
                        "categoria": cat,
                        "gastado": gastado_cat,
                        "limite": limite_cat,
                        "porcentaje": round(pct, 1),
                        "nivel": "ADVERTENCIA",
                        "mensaje": f"Has consumido el {pct:.0f}% del límite en {cat} (${gastado_cat:,.0f} de ${limite_cat:,.0f}).",
                    })

        # Agrupación por comercio (Top 5)
        por_comercio: Dict[str, float] = {}
        for g in gastos_filtrados:
            por_comercio[g.comercio] = por_comercio.get(g.comercio, 0.0) + g.monto
        top_comercios = sorted(por_comercio.items(), key=lambda x: x[1], reverse=True)[:5]

        # Agrupación cronológica por día
        por_dia: Dict[str, float] = {}
        for g in sorted(gastos_filtrados, key=lambda x: x.fecha):
            dia = g.fecha[:10]
            por_dia[dia] = por_dia.get(dia, 0.0) + g.monto

        return {
            "mes": mes_filtro,
            "anio": anio_filtro,
            "total_gastos": len(gastos_filtrados),
            "total_gastado": total_gastado,
            "presupuesto_total": presupuesto_total,
            "restante": restante,
            "porcentaje_consumido": porcentaje_consumido,
            "estado_global": estado_global,
            "color_estado": color_estado,
            "por_categoria": por_categoria,
            "alertas_categoria": alertas_categoria,
            "top_comercios": top_comercios,
            "por_dia": por_dia,
            "gastos_recientes": gastos_filtrados[:10],
        }
