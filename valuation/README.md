# Motor de Valuación — KOKO MLS

Este módulo calcula un **rango de valor** para una propiedad a partir de
anuncios reales recientes del MLS de KOKO. No es un modelo predictivo: es
una agregación estadística transparente, auditable y conservadora.

---

## Para agentes inmobiliarios

### Qué hace y qué no hace

El motor responde una sola pregunta:

> "¿En qué rango de precio se están publicando propiedades parecidas a esta,
> en la misma zona, en los últimos 90 días?"

A partir de los anuncios reales que cumplen ese filtro, devuelve:

- **Precio mínimo** del rango (cuartil 25, el 25% más barato del mercado).
- **Precio mediano** (la mitad del mercado pide menos, la mitad pide más).
- **Precio máximo** del rango (cuartil 75, sin contar valores extremos).
- **Nivel de confianza** según cuántos anuncios sustentan el rango.
- **Los IDs de los anuncios usados**, para que puedas mostrarle al cliente
  exactamente en qué se basa el número.

### Política "Cero datos inventados"

Esta es la regla más importante del motor:

- Si no hay anuncios comparables en los últimos 90 días, el motor **no devuelve
  un número**. Devuelve `confianza = insuficiente` y una nota explicativa.
  No estimamos, no inventamos, no extrapolamos.
- **Las preventas se excluyen siempre.** Sus precios siguen lógicas
  comerciales distintas (descuentos por etapa, entregas a futuro) y mezclarlas
  con propiedades terminadas distorsiona el rango.
- **Solo usamos anuncios en pesos mexicanos.** Si un anuncio está publicado
  en dólares sin tipo de cambio confiable, lo descartamos en lugar de
  inventar una conversión.

### Niveles de confianza

| Anuncios comparables | Nivel de confianza | Qué significa |
|---|---|---|
| 8 o más | **alta** | El rango está bien sustentado. |
| 4 a 7 | **media** | El rango es razonable pero la muestra es modesta. |
| 1 a 3 | **baja** | Hay muy poca evidencia; el rango es solo orientativo. |
| 0 | **insuficiente** | No hay datos para emitir una opinión responsable. |

### ¿Por qué a veces "expandimos" a toda la ciudad?

Si en la zona específica no encontramos al menos 4 anuncios, ampliamos la
búsqueda a toda la ciudad — pero **bajamos un nivel la confianza** para que
quede claro que la comparación es menos precisa. Una casa en una zona
residencial premium no debería compararse a la ligera con una en otra colonia
de la ciudad, aunque tengan tamaño y tipo similares.

```
zona específica  --(<4 anuncios)-->  ciudad completa  →  confianza baja un nivel
```

### ¿Qué son los "valores atípicos" (outliers)?

A veces un anuncio tiene un precio claramente fuera del mercado: un
mecanógrafo se equivocó de cero, un dueño puso un precio "para tantear", una
propiedad regalada por urgencia. Si dejáramos esos valores entrar al cálculo,
arruinarían el rango.

El motor aplica un filtro estadístico clásico (IQR, "rango intercuartílico")
que descarta los valores más alejados de la mayoría. La nota metodológica
que regresa el motor te dice cuántos anuncios se descartaron por esta razón.

### Lo que este motor **NO** hace

- No predice cómo va a moverse el precio en el futuro.
- No evalúa el estado de conservación, vista, materiales, ni reputación de
  la colonia.
- No sustituye a un avalúo profesional cuando hay que dar fe pública
  (créditos hipotecarios, sucesiones, etc.).
- No considera amenidades específicas más allá del tipo de propiedad y la
  zona.

---

## Para ingenieros / personas de datos

### Estructura del módulo

```
valuation/
├── __init__.py        # API pública
├── engine.py          # ValuationEngine: orquesta el pipeline
├── queries.py         # fetch_comparables: SELECT async con filtros
├── outliers.py        # filter_iqr: filtro IQR reusable
├── confidence.py      # classify_confidence: tabla de niveles + downgrade
├── result.py          # ValuationResult: dataclass frozen
└── README.md
```

### Algoritmo (pipeline completo)

```
1. fetch_comparables(zone_id=Z)
   ├── filtros: city + zone + property_type + operation
   │            + active=True + is_preventa=False
   │            + currency='MXN' + scraped_at >= now - 90d
   │
2. ¿len < 4 y zone_id se proporcionó?
   ├── sí → fetch_comparables(zone_id=None)
   │         marcar fallback_to_city=True
   │         geographic_scope = "city"
   └── no → geographic_scope = "zone" (o "city" si llegó así)
   │
3. ¿len == 0?
   ├── sí → return ValuationResult(confianza="insuficiente", precios=None)
   │
4. filter_iqr(precios_por_m2, k=1.5)
   │   — no-op si N<4
   │   — conserva valores en [Q1 - 1.5·IQR, Q3 + 1.5·IQR]
   │
5. percentiles(supervivientes): p25, mediana, p75
   │
6. price_min   = p25     · area_m2
   price_median = mediana · area_m2
   price_max    = p75     · area_m2
   │
7. classify_confidence(N_después_de_outliers, fallback_to_city)
   │
8. return ValuationResult(...)
```

### Tabla de confianza (centralizada en `confidence.py`)

| `n` | `fallback_to_city=False` | `fallback_to_city=True` |
|---|---|---|
| 0 | `insuficiente` | `insuficiente` |
| 1–3 | `baja` | `baja` (no baja más) |
| 4–7 | `media` | `baja` |
| 8+ | `alta` | `media` |

### Esquema de `ValuationResult`

| Campo | Tipo | Descripción |
|---|---|---|
| `confidence_level` | `"alta" / "media" / "baja" / "insuficiente"` | Nivel asignado |
| `comparables_count` | `int` | Anuncios usados (post-outliers) |
| `geographic_scope` | `"zone" / "city" / None` | Alcance final del cálculo |
| `price_min_mxn` | `float / None` | p25 × área |
| `price_median_mxn` | `float / None` | mediana × área |
| `price_max_mxn` | `float / None` | p75 × área |
| `price_per_m2_median` | `float / None` | mediana del $/m² (sin multiplicar) |
| `comparables_used_ids` | `list[UUID]` | IDs auditables de los anuncios usados |
| `computed_at` | `datetime` | UTC |
| `methodology_note` | `str` | Texto explicativo en español |

### Firma pública

```python
class ValuationEngine:
    def __init__(self, session: AsyncSession): ...
    async def compute(
        self,
        *,
        city_id: UUID,
        zone_id: Optional[UUID],
        property_type_id: UUID,
        operation: str,          # "venta" | "renta"
        area_m2: float,
    ) -> ValuationResult: ...
```

### Auditabilidad

`comparables_used_ids` permite reconstruir el cálculo: cada UUID apunta a
una fila `Comparable` específica con su URL, fecha, precio publicado.
Cualquier número que devuelva el motor es **rastreable hasta la lista
original de anuncios reales**.

### Lo que el motor **NO** hace (deliberado)

- No combina monedas. Anuncios en USD se omiten en lugar de convertirse con
  un tipo de cambio inventado.
- No mezcla preventas con propiedades terminadas.
- No produce predicciones (no es un modelo ML). Es un resumen estadístico
  del estado actual del mercado.
- No retorna intervalos de confianza estadísticos formales — la "confianza"
  aquí es una etiqueta de negocio basada en el tamaño de muestra, no un
  intervalo bayesiano ni frecuentista.

### Roadmap natural (fuera del MVP)

- Soporte multi-moneda con tabla de FX auditada.
- Ponderación por antigüedad del anuncio (los recientes pesan más).
- Detección de duplicados entre anuncios del mismo inmueble.
- Calibración de la regla de fallback por ciudad/tipo (ej. ciudades chicas
  donde "zona" y "ciudad" casi coinciden).
