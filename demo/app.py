"""
Dashboard web para visualizar las técnicas de scraping.
Ejecuta cada script bajo demanda y muestra los resultados en tablas/gráficos.

Correr:  python app.py   ->  abre http://127.0.0.1:5000
"""

import atexit
import csv
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from posthog import Posthog

BASE = Path(__file__).parent
EXAMPLES = BASE.parent / "examples"

sys.path.insert(0, str(BASE.parent))
from bytecraw import Scraper

load_dotenv()

posthog_client = Posthog(
    project_api_key=os.environ.get("POSTHOG_PROJECT_TOKEN", ""),
    host=os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com"),
    enable_exception_autocapture=True,
)
atexit.register(posthog_client.shutdown)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bytecraw-dev-secret")


def _get_distinct_id() -> str:
    if "distinct_id" not in session:
        session["distinct_id"] = str(uuid.uuid4())
    return session["distinct_id"]


@app.after_request
def _flush_posthog(response):
    # En serverless (Vercel) la función se congela tras responder y el envío
    # en segundo plano de posthog-python puede perderse: forzamos el flush.
    # Nunca debe tumbar la respuesta si PostHog falla (red, token vacío, etc.).
    try:
        posthog_client.flush()
    except Exception:
        pass
    return response


# Definición de cada técnica: script que ejecuta y archivo de salida que genera.
TECNICAS = {
    "estatico": {
        "titulo": "1 · Static HTML",
        "subtitulo": "requests + BeautifulSoup",
        "sitio": "books.toscrape.com",
        "script": "01_estatico_bs4.py",
        "salida": "libros.csv",
        "descripcion": "The server sends the full HTML. We fetch it and parse it with CSS selectors.",
    },
    "dinamico": {
        "titulo": "2 · Dynamic JS",
        "subtitulo": "Playwright (real browser)",
        "sitio": "quotes.toscrape.com/js",
        "script": "02_dinamico_playwright.py",
        "salida": "frases.json",
        "descripcion": "JS fills the page. We launch a real browser and read the rendered DOM.",
    },
    "api": {
        "titulo": "3 · Intercepted API",
        "subtitulo": "requests → JSON",
        "sitio": "quotes.toscrape.com/api",
        "script": "03_api_red.py",
        "salida": "frases_api.json",
        "descripcion": "Behind the JS there's an API with clean JSON. We hit it and skip the HTML.",
    },
    "scrapy": {
        "titulo": "4 · Scrapy at scale",
        "subtitulo": "crawler with queue + concurrency",
        "sitio": "quotes.toscrape.com",
        "script": "04_scrapy_spider.py",
        "salida": "frases_scrapy.json",
        "descripcion": "Industrial framework: handles URL queue, parallelism, retries and export.",
    },
    "login": {
        "titulo": "5 · API with login",
        "subtitulo": "session + CSRF token",
        "sitio": "quotes.toscrape.com/login",
        "script": "05_api_con_login.py",
        "salida": None,  # solo imprime en consola
        "descripcion": "Data behind a login. We reuse the session cookie/token on every request.",
    },
    "markdown": {
        "titulo": "Extra · HTML → Markdown",
        "subtitulo": "token savings for LLMs",
        "sitio": "quotes.toscrape.com",
        "script": "extra_html_a_markdown.py",
        "salida": "pagina.md",
        "descripcion": "Turns noisy HTML into clean Markdown: same info, a fraction of the tokens.",
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


ANALYZE_I18N = {
    "en": {
        "bad_url": "Enter a URL that starts with http:// or https://",
        "download_err": "Could not download the page: {e}",
        "s1_t": "1 · Tried static HTML",
        "s1_d": "Fetched the page with requests (no browser). Status {status}, "
                "{elapsed}s, {chars} characters of visible text.",
        "s2_browser_t": "2 · Switched to a real browser",
        "s2_browser_d": "The HTML came back nearly empty, so I launched Chromium (Playwright) "
                        "and read the DOM already rendered by JavaScript. {elapsed}s.",
        "s2_missing_t": "2 · Wanted to use a browser",
        "s2_missing_d": "The HTML came back nearly empty (typical of an SPA), but Chromium isn't "
                        "installed. Run 'playwright install chromium' to enable this step.",
        "why_browser": "The static HTML had fewer than 200 characters of text: a typical sign of a page "
                       "that fills itself with JavaScript. So I dropped the fast path and opened a real "
                       "browser to see the final content.",
        "why_missing": "The page seems to need JavaScript, but Chromium is missing. I'm still showing "
                       "what did come through via static HTML.",
        "why_static": "The static HTML already had all the content, so no browser was needed. It's the "
                      "fastest, cheapest path: a single HTTP request, no Chromium.",
        "no_title": "(no title)",
    },
    "es": {
        "bad_url": "Escribe una URL que empiece con http:// o https://",
        "download_err": "No se pudo descargar la página: {e}",
        "s1_t": "1 · Probé HTML estático",
        "s1_d": "Pedí la página con requests (sin navegador). Estado {status}, "
                "{elapsed}s, {chars} caracteres de texto visible.",
        "s2_browser_t": "2 · Cambié a un navegador real",
        "s2_browser_d": "El HTML volvió casi vacío, así que lancé Chromium (Playwright) "
                        "y leí el DOM ya renderizado por JavaScript. {elapsed}s.",
        "s2_missing_t": "2 · Quería usar un navegador",
        "s2_missing_d": "El HTML volvió casi vacío (típico de una SPA), pero Chromium no está "
                        "instalado. Corre 'playwright install chromium' para habilitar este paso.",
        "why_browser": "El HTML estático tenía menos de 200 caracteres de texto: señal típica de una página "
                       "que se rellena con JavaScript. Así que dejé la vía rápida y abrí un navegador real "
                       "para ver el contenido final.",
        "why_missing": "La página parece necesitar JavaScript, pero falta Chromium. Aun así muestro "
                       "lo que sí llegó por HTML estático.",
        "why_static": "El HTML estático ya tenía todo el contenido, así que no hizo falta navegador. Es la "
                      "vía más rápida y barata: una sola petición HTTP, sin Chromium.",
        "no_title": "(sin título)",
    },
    "pt": {
        "bad_url": "Digite uma URL que comece com http:// ou https://",
        "download_err": "Não foi possível baixar a página: {e}",
        "s1_t": "1 · Tentei HTML estático",
        "s1_d": "Busquei a página com requests (sem navegador). Status {status}, "
                "{elapsed}s, {chars} caracteres de texto visível.",
        "s2_browser_t": "2 · Mudei para um navegador real",
        "s2_browser_d": "O HTML voltou quase vazio, então lancei o Chromium (Playwright) "
                        "e li o DOM já renderizado pelo JavaScript. {elapsed}s.",
        "s2_missing_t": "2 · Queria usar um navegador",
        "s2_missing_d": "O HTML voltou quase vazio (típico de uma SPA), mas o Chromium não está "
                        "instalado. Rode 'playwright install chromium' para habilitar este passo.",
        "why_browser": "O HTML estático tinha menos de 200 caracteres de texto: sinal típico de uma página "
                       "que se preenche com JavaScript. Então abandonei o caminho rápido e abri um navegador "
                       "real para ver o conteúdo final.",
        "why_missing": "A página parece precisar de JavaScript, mas falta o Chromium. Ainda assim mostro "
                       "o que veio pelo HTML estático.",
        "why_static": "O HTML estático já tinha todo o conteúdo, então não foi preciso navegador. É o "
                      "caminho mais rápido e barato: uma única requisição HTTP, sem Chromium.",
        "no_title": "(sem título)",
    },
}


@app.route("/analyze", methods=["POST"])
def analyze():
    """Corre la estrategia 'auto' sobre una URL y explica qué hizo y por qué."""
    body = request.json or {}
    lang = body.get("lang", "en")
    tr = ANALYZE_I18N.get(lang, ANALYZE_I18N["en"])
    url = body.get("url", "").strip()
    if not url.startswith(("http://", "https://")):
        return jsonify({"ok": False, "error": tr["bad_url"]}), 400

    bot = Scraper(timeout=20)
    pasos = []
    try:
        page = bot.static(url)
    except Exception as e:
        return jsonify({"ok": False, "error": tr["download_err"].format(e=e)})

    texto = page.soup.get_text(strip=True)
    largo = len(texto)
    pasos.append({
        "titulo": tr["s1_t"],
        "detalle": tr["s1_d"].format(status=page.status, elapsed=page.elapsed, chars=largo),
    })

    uso_navegador = False
    falta_chromium = False
    if largo < 200:
        try:
            page = bot.browser(url)
            uso_navegador = True
            pasos.append({
                "titulo": tr["s2_browser_t"],
                "detalle": tr["s2_browser_d"].format(elapsed=page.elapsed),
            })
        except Exception:
            # En Vercel no hay Chromium (ni binario de Playwright). Cualquier
            # fallo al abrir el navegador -> caemos a "solo estático".
            falta_chromium = True
            pasos.append({
                "titulo": tr["s2_missing_t"],
                "detalle": tr["s2_missing_d"],
            })

    if uso_navegador:
        porque = tr["why_browser"]
    elif falta_chromium:
        porque = tr["why_missing"]
    else:
        porque = tr["why_static"]

    md = ""
    tok_md = None
    try:
        md = page.markdown()
        tok_md = page.tokens(of=md)
    except Exception:
        pass

    try:
        posthog_client.capture(
            _get_distinct_id(),
            "url_analyzed",
            properties={
                "method_used": page.method,
                "used_browser": uso_navegador,
                "chromium_missing": falta_chromium,
                "steps_count": len(pasos),
                "has_markdown": bool(md),
                "token_reduction_ratio": round(tok_md / page.tokens(), 2) if tok_md else None,
            },
        )
    except Exception:
        pass
    return jsonify({
        "ok": True,
        "url": url,
        "method": page.method,
        "steps": pasos,
        "why": porque,
        "titulo": page.css("title") or tr["no_title"],
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
    posthog_client.capture(
        _get_distinct_id(),
        "scrape_technique_run",
        properties={
            "technique": clave,
            "technique_title": t["titulo"],
            "success": proc.returncode == 0,
            "duration_seconds": segundos,
            "record_count": len(data) if isinstance(data, list) else None,
        },
    )
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
    data = leer_salida(TECNICAS[clave]["salida"])
    posthog_client.capture(
        _get_distinct_id(),
        "scrape_data_retrieved",
        properties={
            "technique": clave,
            "has_data": data is not None,
            "record_count": len(data) if isinstance(data, list) else None,
        },
    )
    return jsonify({"ok": True, "data": data})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
