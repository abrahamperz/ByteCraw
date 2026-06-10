"""
Técnica 5 — APIs con login / sesión
====================================
Extensión de la técnica 3: muchos sitios (como tu dashboard de Kapso) guardan
los datos detrás de un login. El flujo es:
  1. Te autenticas (enviando usuario/contraseña, o un token/cookie que copiaste).
  2. Guardas la cookie/token de sesión.
  3. Reutilizas esa sesión en cada petición siguiente.

requests.Session() guarda las cookies automáticamente entre peticiones.

Sitio de práctica: https://quotes.toscrape.com/login
  - Tiene un formulario con un campo oculto "csrf_token" que cambia cada vez.
  - Hay que leerlo primero y enviarlo junto al login (patrón MUY común).
  - Tras loguearte, cada frase muestra un enlace "Goodreads" que solo se ve
    estando autenticado: así comprobamos que la sesión funciona.

Usuario/contraseña de prueba: cualquiera (el sitio acepta lo que sea).

Correr:  python 05_api_con_login.py
"""

import requests
from bs4 import BeautifulSoup

BASE = "https://quotes.toscrape.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (practica-scraping)"}


def obtener_csrf(session: requests.Session) -> str:
    """Lee el token CSRF del formulario de login (campo oculto)."""
    r = session.get(f"{BASE}/login", timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    return soup.select_one('input[name="csrf_token"]')["value"]


def main():
    with requests.Session() as s:
        s.headers.update(HEADERS)

        # 1. Token CSRF + 2. enviar login
        csrf = obtener_csrf(s)
        r = s.post(
            f"{BASE}/login",
            data={"csrf_token": csrf, "username": "practica", "password": "1234"},
            timeout=15,
        )
        r.raise_for_status()

        # 3. Verificar que la sesión quedó autenticada
        soup = BeautifulSoup(r.text, "lxml")
        if soup.select_one('a[href="/logout"]'):
            print("Login correcto: la sesión está autenticada.")
        else:
            print("Login falló (no apareció el enlace de logout).")
            return

        # 4. Usar la sesión para acceder a contenido protegido
        home = s.get(BASE, timeout=15)
        soup = BeautifulSoup(home.text, "lxml")
        enlaces_goodreads = soup.select('a[href*="goodreads.com"]')
        print(f"Enlaces 'Goodreads' visibles solo logueado: {len(enlaces_goodreads)}")
        print("\nMismo patrón aplica a APIs reales: el token va en un header,")
        print("por ejemplo  s.headers['Authorization'] = 'Bearer <token>'")


if __name__ == "__main__":
    main()
