from app.herramientas.herramienta_financiera import HerramientaFinanciera


class FakeTicker:
    fast_info = {
        "lastPrice": 100.0,
        "previousClose": 95.0,
        "marketCap": 123456,
        "currency": "USD",
        "exchange": "NMS",
    }

    def __init__(self, simbolo: str) -> None:
        self.simbolo = simbolo

    def get_info(self) -> dict[str, object]:
        return {
            "longName": "Apple Inc.",
            "currency": "USD",
            "exchange": "NMS",
            "marketCap": 123456,
        }


def test_herramienta_financiera_usa_yahoo_mockeado(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.herramientas.herramienta_financiera.yf.Ticker",
        FakeTicker,
    )

    respuesta = HerramientaFinanciera().consultar("AAPL")

    assert "Apple Inc." in respuesta
    assert "Precio actual: 100.00 USD." in respuesta
    assert "Fuente: Yahoo Finance (fast_info)." in respuesta

