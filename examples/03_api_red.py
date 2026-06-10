"""
Técnica 3 — API / red interceptada
===================================
El truco PRO. Casi siempre que una página carga datos con JS, por debajo está
pidiendo esos datos a una API que devuelve JSON limpio. Si copias esa llamada,
te saltas TODO el HTML y obtienes datos ya estructurados.

Cómo encontrar la API (hazlo en tu navegador):
  1. Abre DevTools (F12) -> pestaña "Network".
  2. Filtra por "Fetch/XHR".
  3. Recarga o interactúa con la página.
  4. Busca peticiones que devuelvan JSON. Esa es la API.
  5. Clic derecho sobre la petición -> "Copy as cURL" para ver headers/tokens.

Sitio de práctica: quotes.toscrape.com tiene un endpoint JSON oculto que su
propio frontend consume:  https://quotes.toscrape.com/api/quotes?page=N

Correr:  python 03_api_red.py
"""

import json
import time

import requests

API = "https://quotes.toscrape.com/api/quotes"
HEADERS = {"User-Agent": "Mozilla/5.0 (practica-scraping)"}


def main():
    resultados = []
    pagina = 1
    with requests.Session() as s:
        s.headers.update(HEADERS)
        while True:
            r = s.get(API, params={"page": pagina}, timeout=15)
            r.raise_for_status()
            data = r.json()  # JSON limpio, sin parsear HTML

            for q in data["quotes"]:
                resultados.append(
                    {
                        "frase": q["text"],
                        "autor": q["author"]["name"],
                        "tags": q["tags"],
                    }
                )

            if not data.get("has_next"):
                break
            pagina += 1
            time.sleep(0.3)

    print(f"Total de frases: {len(resultados)}")
    with open("frases_api.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print("Guardado en frases_api.json")
    print("\nNota: compara la VELOCIDAD de este script vs 02_dinamico_playwright.py.")
    print("Misma data, pero sin abrir navegador = muchísimo más rápido y estable.")


if __name__ == "__main__":
    main()
