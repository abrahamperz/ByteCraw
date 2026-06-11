"""
Dashboard web para visualizar las técnicas de scraping.
Ejecuta cada script bajo demanda y muestra los resultados en tablas/gráficos.

Correr:  python app.py   ->  abre http://127.0.0.1:5000
"""

import csv
import json
import subprocess
import sys
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request

BASE = Path(__file__).parent
EXAMPLES = BASE.parent / "examples"

sys.path.insert(0, str(BASE.parent))
from bytecraw import Scraper

app = Flask(__name__)

# Definición de cada técnica: script que ejecuta y archivo de salida que genera.
TECNICAS = {
    "estatico": {
        "titulo": "1 · HTML estático",
        "subtitulo": "requests + BeautifulSoup",
        "sitio": "books.toscrape.com",
        "script": "01_estatico_bs4.py",
        "salida": "libros.csv",
        "descripcion": "El servidor manda el HTML completo. Lo pedimos y parseamos con selectores CSS.",
    },
    "dinamico": {
        "titulo": "2 · JS dinámico",
        "subtitulo": "Playwright (navegador real)",
        "sitio": "quotes.toscrape.com/js",
        "script": "02_dinamico_playwright.py",
        "salida": "frases.json",
        "descripcion": "El JS rellena la página. Lanzamos un navegador real y leemos el DOM ya pintado.",
    },
    "api": {
        "titulo": "3 · API interceptada",
        "subtitulo": "requests → JSON",
        "sitio": "quotes.toscrape.com/api",
        "script": "03_api_red.py",
        "salida": "frases_api.json",
        "descripcion": "Detrás del JS hay una API con JSON limpio. La copiamos y nos saltamos el HTML.",
    },
    "scrapy": {
        "titulo": "4 · Scrapy a escala",
        "subtitulo": "crawler con cola + concurrencia",
        "sitio": "quotes.toscrape.com",
        "script": "04_scrapy_spider.py",
        "salida": "frases_scrapy.json",
        "descripcion": "Framework industrial: maneja cola de URLs, paralelismo, reintentos y export.",
    },
    "login": {
        "titulo": "5 · API con login",
        "subtitulo": "sesión + token CSRF",
        "sitio": "quotes.toscrape.com/login",
        "script": "05_api_con_login.py",
        "salida": None,  # solo imprime en consola
        "descripcion": "Datos detrás de login. Reutilizamos la cookie/token de sesión en cada petición.",
    },
    "markdown": {
        "titulo": "Extra · HTML → Markdown",
        "subtitulo": "ahorro de tokens para LLMs",
        "sitio": "quotes.toscrape.com",
        "script": "extra_html_a_markdown.py",
        "salida": "pagina.md",
        "descripcion": "Convierte el HTML ruidoso a Markdown limpio: misma info, fracción de tokens.",
    },
}


def leer_salida(nombre: str):
    """Lee el archivo de resultados y lo devuelve como estructura para la UI."""
    if not nombre:
        return None
    ruta = EXAMPLES / nombre
    if not ruta.exists():
        return None
    if nombre.endswith(".json"):
        return json.loads(ruta.read_text(encoding="utf-8"))
    if nombre.endswith(".csv"):
        with ruta.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))
    if nombre.endswith(".md"):
        return ruta.read_text(encoding="utf-8")
    return None


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/methods")
def methods():
    return render_template("index.html", tecnicas=TECNICAS)


@app.route("/try")
def try_playground():
    return render_template("try.html", tecnicas=TECNICAS)


@app.route("/analyze", methods=["POST"])
def analyze():
    """Corre la estrategia 'auto' sobre una URL y explica qué hizo y por qué."""
    url = (request.json or {}).get("url", "").strip()
    if not url.startswith(("http://", "https://")):
        return jsonify({"ok": False, "error": "Enter a URL that starts with http:// or https://"}), 400

    bot = Scraper(timeout=20)
    pasos = []
    try:
        page = bot.static(url)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Could not download the page: {e}"})

    texto = page.soup.get_text(strip=True)
    largo = len(texto)
    pasos.append({
        "titulo": "1 · Tried static HTML",
        "detalle": f"Fetched the page with requests (no browser). Status {page.status}, "
                   f"{page.elapsed}s, {largo} characters of visible text.",
    })

    uso_navegador = False
    falta_chromium = False
    if largo < 200:
        try:
            page = bot.browser(url)
            uso_navegador = True
            pasos.append({
                "titulo": "2 · Switched to a real browser",
                "detalle": f"The HTML came back nearly empty, so I launched Chromium (Playwright) "
                           f"and read the DOM already rendered by JavaScript. {page.elapsed}s.",
            })
        except ImportError:
            falta_chromium = True
            pasos.append({
                "titulo": "2 · Wanted to use a browser",
                "detalle": "The HTML came back nearly empty (typical of an SPA), but Chromium isn't "
                           "installed. Run 'playwright install chromium' to enable this step.",
            })

    if uso_navegador:
        porque = ("The static HTML had fewer than 200 characters of text: a typical sign of a page "
                  "that fills itself with JavaScript. So I dropped the fast path and opened a real "
                  "browser to see the final content.")
    elif falta_chromium:
        porque = ("The page seems to need JavaScript, but Chromium is missing. I'm still showing "
                  "what did come through via static HTML.")
    else:
        porque = ("The static HTML already had all the content, so no browser was needed. It's the "
                  "fastest, cheapest path: a single HTTP request, no Chromium.")

    md = ""
    tok_md = None
    try:
        md = page.markdown()
        tok_md = page.tokens(of=md)
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "url": url,
        "method": page.method,
        "steps": pasos,
        "why": porque,
        "titulo": page.css("title") or "(no title)",
        "links": len(page.links()),
        "tokens_html": page.tokens(),
        "tokens_md": tok_md,
        "sample_md": md,
    })


@app.route("/docs")
def docs():
    return render_template("docs.html")


@app.route("/run/<clave>", methods=["POST"])
def run(clave):
    if clave not in TECNICAS:
        return jsonify({"ok": False, "error": "técnica desconocida"}), 404

    t = TECNICAS[clave]
    inicio = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, t["script"]],
            cwd=EXAMPLES,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "el script tardó demasiado (timeout)"}), 504
    segundos = round(time.perf_counter() - inicio, 2)

    data = leer_salida(t["salida"])
    return jsonify(
        {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-2000:],
            "salida": t["salida"],
            "data": data,
            "segundos": segundos,
        }
    )


@app.route("/data/<clave>")
def data(clave):
    """Devuelve resultados ya generados sin re-ejecutar el script."""
    if clave not in TECNICAS:
        return jsonify({"ok": False}), 404
    return jsonify({"ok": True, "data": leer_salida(TECNICAS[clave]["salida"])})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
