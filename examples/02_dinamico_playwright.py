"""
Técnica 2 — JS dinámico con Playwright (navegador real)
========================================================
Cuando el HTML inicial llega casi vacío y el JavaScript rellena el contenido
(apps tipo React/Vue, como tu dashboard de Kapso), no sirve requests.
Lanzamos un navegador real, dejamos que ejecute el JS y leemos el DOM ya renderizado.

Sitio de práctica: https://quotes.toscrape.com/js (las frases se cargan por JS)

Cómo saber si necesitas esto:
  - "Ver código fuente" sale vacío PERO en pantalla sí ves los datos.
  - Eso significa que el JS los inyectó después de cargar.

Antes de correr (una sola vez):
  pip install playwright
  playwright install chromium

Correr:  python 02_dinamico_playwright.py
"""

import json

from playwright.sync_api import sync_playwright


def main():
    resultados = []
    with sync_playwright() as p:
        # headless=False para VER el navegador (útil al aprender / depurar)
        navegador = p.chromium.launch(headless=True)
        pagina = navegador.new_page()

        pagina.goto("https://quotes.toscrape.com/js", wait_until="networkidle")

        while True:
            # Esperamos a que el JS pinte las frases antes de leerlas
            pagina.wait_for_selector("div.quote")

            for q in pagina.query_selector_all("div.quote"):
                texto = q.query_selector("span.text").inner_text()
                autor = q.query_selector("small.author").inner_text()
                tags = [t.inner_text() for t in q.query_selector_all("a.tag")]
                resultados.append({"frase": texto, "autor": autor, "tags": tags})

            # Paginación: si hay botón "Next", clic y repetimos
            siguiente = pagina.query_selector("li.next a")
            if not siguiente:
                break
            siguiente.click()
            pagina.wait_for_load_state("networkidle")

        navegador.close()

    print(f"Total de frases: {len(resultados)}")
    with open("frases.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print("Guardado en frases.json")


if __name__ == "__main__":
    main()
