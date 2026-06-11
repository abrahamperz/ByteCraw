# Estrategia mental

Ante un sitio nuevo, prueba en este orden:

1. **¿Hay una API por detrás?** → datos JSON limpios, lo mejor.
2. **¿El HTML es estático?** → rápido y sencillo.
3. **¿Solo se ve con JavaScript?** → saca el navegador.
4. **¿Son muchas páginas?** → crawling con paginación.
5. **¿Está detrás de login?** → sesión autenticada.
6. **¿Explorar un sitio entero por tema o importancia?** → crawling de grafos.

`bot.fetch(url, strategy="auto")` aplica esto solo: prueba estático y, si la
página viene casi vacía (típico de SPAs), reintenta con navegador.

---

[← Volver al índice](../README.md) · [Siguiente: Nota ética →](nota-etica.md)
