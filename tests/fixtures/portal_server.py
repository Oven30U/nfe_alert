"""
Servidor HTTP local, en un thread, que sirve páginas HTML estáticas para
simular el comportamiento de un portal fiscal en los 3 escenarios que
importan para distinguir credenciales inválidas de timeouts de portal:

  /login_success.html                -> login exitoso
  /login_credenciales_invalidas.html -> mensaje explícito de error de credenciales
  /login_timeout.html                -> nunca muestra éxito NI mensaje de error
                                         (simula portal caído / lento / colgado)
  /afip_login_success.html, /afip_login_credenciales.html, /afip_login_hang.html
                                      -> variantes que imitan los selectores
                                         usados por Jurisdiccion.AFIP_login

No se usan credenciales, sitios ni datos reales. Es únicamente HTML estático
en disco, servido en 127.0.0.1 con un puerto libre.
"""
from __future__ import annotations

import http.server
import socket
import threading
from pathlib import Path

HTML_DIR = Path(__file__).resolve().parent / "html"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HTML_DIR), **kwargs)

    def log_message(self, format, *args):  # silenciar logs de test
        pass


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class PortalTestServer:
    def __init__(self):
        self.port = _free_port()
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", self.port), _Handler)
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def url(self, path: str) -> str:
        path = path.lstrip("/")
        return f"http://127.0.0.1:{self.port}/{path}"
