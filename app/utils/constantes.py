PATRON_TICKER = r"\b[A-Z]{1,5}(?:\.[A-Z]{1,2})?\b"

EMPRESAS_CONOCIDAS: dict[str, str] = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "nvidia": "NVDA",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
    "mercado libre": "MELI",
    "mercadolibre": "MELI",
    "coca cola": "KO",
    "coca-cola": "KO",
    "walmart": "WMT",
    "disney": "DIS",
}

PALABRAS_FINANCIERAS = (
    "accion",
    "acciones",
    "bolsa",
    "cotiza",
    "cotizacion",
    "financ",
    "market cap",
    "mercado",
    "precio",
    "ticker",
    "variacion",
    "valor",
    "yahoo",
)

PALABRAS_NO_TICKER = frozenset({"API", "CEO", "USD", "IA", "AI"})

PALABRAS_META_HISTORIAL = (
    "que te pregunte",
    "que me preguntaste",
    "que te dije",
    "que me dijiste",
    "que me respondiste",
    "que me contestaste",
    "que hablamos",
    "de que hablamos",
    "ultima pregunta",
    "ultimo mensaje",
    "acabo de preguntar",
    "acabo de decir",
    "me acabas de",
    "acabas de decir",
    "acabas de responder",
    "repetilo",
    "repeti eso",
    "acordas",
    "recordas",
    "lo anterior",
    "antes pregunte",
)
