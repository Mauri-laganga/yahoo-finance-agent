import logging


def configurar_logs(nivel: str) -> None:
    logging.basicConfig(
        level=getattr(logging, nivel.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
