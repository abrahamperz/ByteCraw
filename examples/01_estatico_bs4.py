"""
Técnica 1 — HTML estático con requests + BeautifulSoup
=======================================================
El servidor devuelve el HTML ya completo. Lo pedimos, lo parseamos
y extraemos con selectores CSS.

Sitio de práctica: https://books.toscrape.com (catálogo estático de libros)

Cómo saber si sirve esta técnica:
  - Abre la página, clic derecho -> "Ver código fuente".
  - Si los datos que quieres ya aparecen ahí (no vacío), esta técnica funciona.

Correr:  python 01_estatico_bs4.py
"""

import csv
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://books.toscrape.com/catalogue/"
START = "https://books.toscrape.com/catalogue/page-1.html"

# Header de navegador real: muchos servidores rechazan el User-Agent por defecto
# de requests ("python-requests/2.x"). Esto es buena práctica básica.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# Mapeo de la clase CSS de la valoración a un número
RATING = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def parse_page(html: str):
    """Extrae todos los libros de una página de catálogo."""
    soup = BeautifulSoup(html, "lxml")
    libros = []
    for card in soup.select("article.product_pod"):
        titulo = card.h3.a["title"]
        precio = card.select_one("p.price_color").text.strip()
        rating_clase = card.select_one("p.star-rating")["class"][1]  # ej. "Three"
        disponible = card.select_one("p.instock.availability").text.strip()
        libros.append(
            {
                "titulo": titulo,
                "precio": precio,
                "rating": RATING.get(rating_clase, 0),
                "disponibilidad": disponible,
            }
        )
    return libros


def next_url(html: str):
    """Devuelve la URL de la siguiente página, o None si es la última."""
    soup = BeautifulSoup(html, "lxml")
    nxt = soup.select_one("li.next a")
    return BASE + nxt["href"] if nxt else None


def main():
    url = START
    todos = []
    # Reutilizamos la conexión TCP con una Session -> más rápido en muchas peticiones
    with requests.Session() as s:
        s.headers.update(HEADERS)
        while url:
            print(f"Descargando: {url}")
            r = s.get(url, timeout=15)
            r.raise_for_status()
            todos.extend(parse_page(r.text))
            url = next_url(r.text)
            time.sleep(0.5)  # rate limit básico: no martillear el servidor

    print(f"\nTotal de libros: {len(todos)}")
    with open("libros.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["titulo", "precio", "rating", "disponibilidad"])
        w.writeheader()
        w.writerows(todos)
    print("Guardado en libros.csv")


if __name__ == "__main__":
    main()
