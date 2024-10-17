import granian
from granian.constants import Interfaces, Loops

from app.settings import get_settings


if __name__ == "__main__":
    settings = get_settings()
    granian.Granian(
        target="application:application",
        address="0.0.0.0",  # noqa: S104
        port=settings.app_port,
        interface=Interfaces.ASGI,
        log_dictconfig={"root": {"level": "INFO"}} if not settings.debug else {},
        log_level=settings.log_level,
        loop=Loops.uvloop,
    ).serve()
