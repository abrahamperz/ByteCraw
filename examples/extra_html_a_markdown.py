"""
EXTRA — HTML a Markdown para ahorrar tokens en LLMs
====================================================
Tu intuición es correcta: si vas a pasarle una página a un LLM para que extraiga
datos, el HTML crudo está LLENO de ruido (<div>, clases, estilos, scripts) que
consume muchísimos tokens sin aportar información.

Convertir ese HTML a Markdown limpio:
  - elimina tags, atributos, estilos y scripts,
  - conserva el contenido y la estructura (títulos, listas, tablas, enlaces),
  - reduce el conteo de tokens típicamente entre 5x y 10x.

Dos herramientas:
  - markdownify: convierte HTML -> Markdown directo.
  - trafilatura: además detecta y extrae SOLO el contenido principal
                 (quita menús, banners, footers) -> aún menos tokens.

Antes de correr:  pip install requests markdownify trafilatura
Correr:           python extra_html_a_markdown.py
"""

import requests
from markdownify import markdownify
import trafilatura

URL = "https://quotes.toscrape.com/"
HEADERS = {"User-Agent": "Mozilla/5.0 (practica-scraping)"}


def estimar_tokens(texto: str) -> int:
    """Aproximación rápida: ~4 caracteres por token en inglés/español."""
    return len(texto) // 4


def main():
    html = requests.get(URL, headers=HEADERS, timeout=15).text

    # Opción A: markdownify (convierte todo el HTML)
    md_completo = markdownify(html, strip=["script", "style"])

    # Opción B: trafilatura (extrae solo el contenido principal, en markdown)
    md_principal = trafilatura.extract(html, output_format="markdown") or ""

    print("=== Comparación de tamaño (tokens aproximados) ===")
    print(f"HTML crudo:            ~{estimar_tokens(html):>6} tokens")
    print(f"Markdown (markdownify):~{estimar_tokens(md_completo):>6} tokens")
    print(f"Markdown (trafilatura):~{estimar_tokens(md_principal):>6} tokens")

    with open("pagina.md", "w", encoding="utf-8") as f:
        f.write(md_principal or md_completo)
    print("\nGuardado el markdown limpio en pagina.md")
    print("Ese .md es lo que le pasarías a un LLM: misma info, fracción de tokens.")


if __name__ == "__main__":
    main()
