# ByteCraw

Una sola API de Python para scrapear cualquier sitio: HTML estático, JS dinámico,
APIs ocultas, login con sesión, crawling y Markdown listo para LLMs.

- **Demo**: https://byte-craw.vercel.app/
- **PyPI**: https://pypi.org/project/bytecraw/
- **GitHub**: https://github.com/abrahamperz/ByteCraw

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install bytecraw         # trae todo: estático, APIs, Markdown y navegador
python3 -m playwright install chromium  # solo si usas .browser()
```

## Quickstart

```python
from bytecraw import Scraper

bot = Scraper(delay=0.5)
page = bot.static("https://books.toscrape.com")

print(page.status, page.method, page.elapsed)
print(page.css("h1"))
```

## Las técnicas

Cada estrategia es un método explícito del `Scraper`. El orden, de lo más limpio
a lo más costoso: API → estático → navegador → crawling → sesión.

### 1 · HTML estático

Para sitios donde el servidor ya manda el HTML completo. Una petición HTTP,
parseo con selectores CSS (soporta `::text` y `::attr(nombre)`).

```python
page = bot.static("https://books.toscrape.com")

libros = page.extract("article.product_pod", {
    "titulo": "h3 a::attr(title)",
    "precio": "p.price_color::text",
})
```

### 2 · JS dinámico (navegador)

Cuando el contenido lo rellena JavaScript, abre un Chromium real (Playwright)
y lee el DOM ya pintado. Puedes esperar a un selector o hacer scroll para lazy load.

```python
page = bot.browser("https://quotes.toscrape.com/js", scroll=True)
print(page.css_all("span.text"))
```

### 3 · API oculta (JSON)

Detrás del JS casi siempre hay una API con JSON limpio. La pides directo y te
saltas el HTML por completo: lo más rápido y estable.

```python
data = bot.api("https://quotes.toscrape.com/api/quotes", params={"page": 1})
print(data.json())
```

### 4 · Crawling con paginación

Recorre múltiples páginas siguiendo el enlace "siguiente" y junta todos los registros.

```python
items = bot.crawl(
    "https://quotes.toscrape.com",
    item="div.quote",
    fields={"frase": "span.text::text", "tags[]": "a.tag::text"},
    next="li.next a::attr(href)",
)
```

### 5 · Login con sesión (CSRF / bearer)

Reutiliza la cookie o token de sesión en cada petición para acceder a datos
detrás de un login.

```python
s = bot.session().login(url, data=creds, csrf_field="csrf_token")
home = s.fetch("https://quotes.toscrape.com")

# o con token:
s = bot.session().bearer("eyJhbGci...")
```

### Markdown para LLMs

Convierte el HTML ruidoso en Markdown limpio: misma info, fracción de tokens.

```python
md = page.markdown()                 # solo el contenido principal
md_full = page.markdown(main_only=False)  # toda la página
print(page.tokens(), "->", page.tokens(of=md))
```

## Estrategia mental

Ante un sitio nuevo, prueba en este orden:

1. **¿Hay una API por detrás?** → datos JSON limpios, lo mejor.
2. **¿El HTML es estático?** → rápido y sencillo.
3. **¿Solo se ve con JavaScript?** → saca el navegador.
4. **¿Son muchas páginas?** → crawling con paginación.
5. **¿Está detrás de login?** → sesión autenticada.

`bot.fetch(url, strategy="auto")` aplica esto solo: prueba estático y, si la
página viene casi vacía (típico de SPAs), reintenta con navegador.

## Nota ética

Respeta `robots.txt` y los Términos de Servicio de cada sitio, y no abuses del
rate limit (usa `delay`). Scrapea sitios hechos para ello o tus propios sistemas.

## Licencia

MIT
