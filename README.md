# Proyecto de práctica: Web Scraping

5 técnicas de scraping + manejo de CAPTCHAs + truco de tokens, sobre sitios
de práctica legales (`toscrape.com`).

## Instalar desde PyPI

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install bytecraw         # trae todo: estático, APIs, Markdown y navegador
python3 -m playwright install chromium  # solo si usas .browser()
```

`bytecraw` ya incluye todas las dependencias (requests, beautifulsoup4, lxml,
markdownify, trafilatura y playwright). El único paso extra es descargar el
navegador con `playwright install chromium`, y solo si vas a usar `.browser()`.

## La librería `bytecraw/`

Las 5 técnicas envueltas en una sola API limpia (estilo SDK).

```python
from bytecraw import Scraper

bot = Scraper(delay=0.5)

# Estrategias explícitas
page = bot.static("https://books.toscrape.com")          # 1 · HTML estático
page = bot.browser("https://quotes.toscrape.com/js")     # 2 · JS dinámico
data = bot.api("https://quotes.toscrape.com/api/quotes") # 3 · API JSON
page = bot.fetch(url, strategy="auto")                   # auto: estático -> navegador

# Extraer registros con selectores (soporta ::text y ::attr(nombre))
libros = page.extract("article.product_pod", {
    "titulo": "h3 a::attr(title)",
    "precio": "p.price_color::text",
})

# Crawling con paginación
items = bot.crawl(url, item="div.quote",
    fields={"frase": "span.text::text", "tags[]": "a.tag::text"},
    next="li.next a::attr(href)")

# 5 · Sesión con login + CSRF
s = bot.session().login(url, data=creds, csrf_field="csrf_token")
home = s.fetch("https://quotes.toscrape.com")

# LLM: HTML -> Markdown limpio (menos tokens)
md = page.markdown()
print(page.tokens(), "->", page.tokens(of=md))
```

## Landing page + dashboard

- `http://127.0.0.1:5000/landing` — landing estilo Vercel/chat-sdk.dev
- `http://127.0.0.1:5000/` — dashboard interactivo (ejecuta cada técnica + tiempos)

## La estrategia mental

Ante un sitio nuevo, prueba en este orden (de más limpio a más costoso):

1. **¿Hay una API por detrás?** (técnica 3) → datos JSON limpios, lo mejor.
2. **¿El HTML es estático?** (técnica 1) → rápido y sencillo.
3. **¿Solo se ve con JavaScript?** (técnica 2) → saca el navegador.
4. **¿Son miles de páginas?** (técnica 4) → Scrapy.
5. **¿Está detrás de login?** (técnica 5) → sesión autenticada.

## Archivos

| Archivo | Técnica | Sitio | Genera |
|---|---|---|---|
| `01_estatico_bs4.py` | 1. HTML estático (requests + BeautifulSoup) | books.toscrape.com | `libros.csv` |
| `02_dinamico_playwright.py` | 2. JS dinámico (Playwright) | quotes.toscrape.com/js | `frases.json` |
| `03_api_red.py` | 3. API interceptada | quotes.toscrape.com/api | `frases_api.json` |
| `04_scrapy_spider.py` | 4. Scrapy a escala | quotes.toscrape.com | `frases_scrapy.json` |
| `05_api_con_login.py` | 5. API con login/sesión | quotes.toscrape.com/login | (consola) |
| `extra_captcha.py` | Manejo de CAPTCHAs | (notas + ejemplos) | — |
| `extra_html_a_markdown.py` | HTML→Markdown (ahorro de tokens) | quotes.toscrape.com | `pagina.md` |

## Instalación

```bash
cd /Users/array101/scrapping
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # solo para la técnica 2
```

## Cómo aprender con esto

1. Corre `03_api_red.py` y luego `02_dinamico_playwright.py`: misma data,
   compara la velocidad. Entenderás por qué buscar la API primero.
2. Corre `01_estatico_bs4.py` para el caso clásico estático.
3. Corre `04_scrapy_spider.py` para ver el crawling a escala.
4. Corre `05_api_con_login.py` para el patrón de sesión + token CSRF
   (es el patrón que aplicarías a tu dashboard de Kapso).
5. Lee `extra_captcha.py` y corre `extra_html_a_markdown.py`.

## Nota ética

Practica en sitios hechos para ello (`toscrape.com`) o en tus propios sistemas.
Respeta `robots.txt` y los Términos de Servicio. No abuses del rate limit.
