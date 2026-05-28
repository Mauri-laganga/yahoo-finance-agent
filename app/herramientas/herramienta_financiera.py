import logging
from dataclasses import dataclass
from typing import Any

import yfinance as yf
from langchain_core.tools import StructuredTool, tool

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InfoAccion:
    simbolo: str
    precio_actual: float | None = None
    variacion: float | None = None
    variacion_porcentual: float | None = None
    market_cap: int | None = None
    moneda: str | None = None
    empresa: str | None = None
    mercado: str | None = None
    fuente: str | None = None
    error: str | None = None

    @property
    def tiene_datos(self) -> bool:
        return any(
            valor is not None
            for valor in (
                self.precio_actual,
                self.variacion,
                self.market_cap,
                self.moneda,
                self.empresa,
                self.mercado,
            )
        )


@tool("consultar_finanzas_yahoo")
def consultar_finanzas_yahoo(simbolo: str) -> str:
    """Consulta precio, variación, market cap, moneda y metadata en Yahoo Finance."""
    return HerramientaFinanciera().consultar(simbolo)


class HerramientaFinanciera:
    def __init__(self) -> None:
        self.tool = StructuredTool.from_function(
            func=self.consultar,
            name="consultar_finanzas_yahoo",
            description=(
                "Consulta precio actual, variación, market cap, moneda, "
                "empresa y mercado de un símbolo financiero usando Yahoo Finance."
            ),
        )

    def ejecutar_como_tool(self, simbolo: str) -> str:
        return str(self.tool.invoke({"simbolo": simbolo}))

    def consultar(self, simbolo: str) -> str:
        info_accion = self.obtener_info_accion(simbolo)
        return self._formatear_info_accion(info_accion)

    def obtener_info_accion(self, simbolo: str) -> InfoAccion:
        simbolo_limpio = simbolo.strip().upper()
        logger.info("Yahoo Finance: símbolo recibido=%s", simbolo_limpio)

        if not simbolo_limpio:
            raise ValueError("El símbolo financiero no puede estar vacío.")

        try:
            ticker = yf.Ticker(simbolo_limpio)
        except Exception as error:
            logger.exception("Error inicializando Yahoo Finance para %s", simbolo_limpio)
            return InfoAccion(
                simbolo=simbolo_limpio,
                error=f"No pude inicializar Yahoo Finance para {simbolo_limpio}: {error}",
            )

        datos_fast_info = self._obtener_datos_desde_fast_info(ticker)
        metadata = self._obtener_metadata_basica(ticker)

        if self._datos_validos(datos_fast_info):
            logger.info(
                "Yahoo Finance: usando fast_info para %s con datos=%s",
                simbolo_limpio,
                self._resumen_log(datos_fast_info | metadata),
            )
            return self._armar_info_accion(
                simbolo=simbolo_limpio,
                datos=datos_fast_info | metadata,
                fuente="fast_info",
            )

        logger.info("Yahoo Finance: fast_info sin datos válidos para %s; usando history(period='1d')", simbolo_limpio)
        datos_historial = self._obtener_datos_desde_historial(ticker, simbolo_limpio)

        if self._datos_validos(datos_historial):
            logger.info(
                "Yahoo Finance: usando history para %s con datos=%s",
                simbolo_limpio,
                self._resumen_log(datos_historial | metadata),
            )
            return self._armar_info_accion(
                simbolo=simbolo_limpio,
                datos=datos_historial | metadata,
                fuente="history",
            )

        logger.warning(
            "Yahoo Finance: no se encontraron datos financieros para %s. fast_info=%s history=%s metadata=%s",
            simbolo_limpio,
            self._resumen_log(datos_fast_info),
            self._resumen_log(datos_historial),
            self._resumen_log(metadata),
        )
        return InfoAccion(
            simbolo=simbolo_limpio,
            empresa=metadata.get("empresa"),
            moneda=metadata.get("moneda"),
            mercado=metadata.get("mercado"),
            error=f"No encontré información financiera para {simbolo_limpio}.",
        )

    def _obtener_datos_desde_fast_info(self, ticker: Any) -> dict[str, Any]:
        try:
            fast_info = ticker.fast_info
        except Exception as error:
            logger.warning("Yahoo Finance: error obteniendo fast_info: %s", error)
            return {}

        datos = {
            "precio_actual": self._leer_fast_info(fast_info, "lastPrice", "last_price"),
            "precio_anterior": self._leer_fast_info(
                fast_info,
                "previousClose",
                "previous_close",
                "regularMarketPreviousClose",
            ),
            "market_cap": self._leer_fast_info(fast_info, "marketCap", "market_cap"),
            "moneda": self._leer_fast_info(fast_info, "currency", "moneda"),
            "mercado": self._leer_fast_info(fast_info, "exchange", "mercado"),
        }
        logger.debug("Yahoo Finance: respuesta fast_info=%s", self._resumen_log(datos))
        return datos

    def _leer_fast_info(self, fast_info: Any, *claves: str) -> Any:
        for clave in claves:
            try:
                if hasattr(fast_info, "get"):
                    valor = fast_info.get(clave)
                else:
                    valor = fast_info[clave]
            except Exception as error:
                logger.debug("Yahoo Finance: no se pudo leer fast_info[%s]: %s", clave, error)
                continue

            if valor is not None:
                return valor
        return None

    def _obtener_metadata_basica(self, ticker: Any) -> dict[str, Any]:
        try:
            info = ticker.get_info()
        except Exception as error:
            logger.info("Yahoo Finance: metadata opcional no disponible: %s", error)
            return {}

        datos = {
            "empresa": info.get("longName") or info.get("shortName"),
            "moneda": info.get("currency"),
            "mercado": info.get("exchange"),
            "market_cap": info.get("marketCap"),
        }
        logger.debug("Yahoo Finance: respuesta metadata=%s", self._resumen_log(datos))
        return {clave: valor for clave, valor in datos.items() if valor is not None}

    def _obtener_datos_desde_historial(self, ticker: Any, simbolo: str) -> dict[str, Any]:
        try:
            historial = ticker.history(period="1d")
        except Exception as error:
            logger.warning("Yahoo Finance: error obteniendo history(period='1d') para %s: %s", simbolo, error)
            return {}

        if historial is None or historial.empty:
            logger.warning("Yahoo Finance: history(period='1d') vino vacío para %s", simbolo)
            return {}

        try:
            cierre = historial["Close"].dropna()
            precio_actual = float(cierre.iloc[-1]) if not cierre.empty else None
        except Exception as error:
            logger.warning("Yahoo Finance: no se pudo leer precio desde history para %s: %s", simbolo, error)
            precio_actual = None

        datos = {"precio_actual": precio_actual}
        logger.debug("Yahoo Finance: respuesta history=%s", self._resumen_log(datos))
        return datos

    def _datos_validos(self, datos: dict[str, Any]) -> bool:
        return datos.get("precio_actual") is not None or datos.get("market_cap") is not None

    def _armar_info_accion(
        self,
        *,
        simbolo: str,
        datos: dict[str, Any],
        fuente: str,
    ) -> InfoAccion:
        precio_actual = self._convertir_float(datos.get("precio_actual"))
        precio_anterior = self._convertir_float(datos.get("precio_anterior"))

        variacion = None
        variacion_porcentual = None
        if precio_actual is not None and precio_anterior:
            variacion = float(precio_actual) - float(precio_anterior)
            variacion_porcentual = (variacion / float(precio_anterior)) * 100

        return InfoAccion(
            simbolo=simbolo,
            empresa=datos.get("empresa") or simbolo,
            precio_actual=precio_actual,
            variacion=variacion,
            variacion_porcentual=variacion_porcentual,
            market_cap=self._convertir_int(datos.get("market_cap")),
            moneda=datos.get("moneda"),
            mercado=datos.get("mercado"),
            fuente=fuente,
        )

    def _formatear_info_accion(self, info_accion: InfoAccion) -> str:
        if info_accion.error and not info_accion.tiene_datos:
            return info_accion.error

        partes = [
            f"Empresa: {info_accion.empresa or info_accion.simbolo} ({info_accion.simbolo}).",
        ]

        if info_accion.precio_actual is not None:
            partes.append(
                f"Precio actual: {self._formatear_numero(info_accion.precio_actual)} "
                f"{info_accion.moneda or ''}."
            )

        if info_accion.variacion is not None and info_accion.variacion_porcentual is not None:
            partes.append(
                "Variación vs cierre previo: "
                f"{self._formatear_numero(info_accion.variacion)} "
                f"({info_accion.variacion_porcentual:.2f}%)."
            )

        if info_accion.market_cap is not None:
            partes.append(f"Market cap: {self._formatear_entero(info_accion.market_cap)}.")

        if info_accion.mercado:
            partes.append(f"Mercado: {info_accion.mercado}.")

        if info_accion.fuente:
            partes.append(f"Fuente: Yahoo Finance ({info_accion.fuente}).")

        return " ".join(partes)

    def _convertir_float(self, valor: Any) -> float | None:
        if valor is None:
            return None
        try:
            return float(valor)
        except (TypeError, ValueError):
            return None

    def _convertir_int(self, valor: Any) -> int | None:
        if valor is None:
            return None
        try:
            return int(valor)
        except (TypeError, ValueError):
            return None

    def _resumen_log(self, datos: dict[str, Any]) -> dict[str, Any]:
        return {clave: valor for clave, valor in datos.items() if valor is not None}

    def _formatear_numero(self, valor: Any) -> str:
        if valor is None:
            return "no disponible"
        return f"{float(valor):,.2f}"

    def _formatear_entero(self, valor: Any) -> str:
        return f"{int(valor):,}"
