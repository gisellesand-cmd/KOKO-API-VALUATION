# Tests del motor de valuación

Dependencias de desarrollo asumidas (todavía no hay `pyproject.toml`):

```
pytest
pytest-asyncio
sqlalchemy[asyncio]
aiosqlite
numpy
```

Las pruebas se ejecutan con `pytest` desde la raíz del repo. Usan una base de
datos SQLite en memoria mediante `aiosqlite`, así que no requieren Postgres
para correr localmente.

> Nota: el módulo `db/models/` actualmente es un *stub*. Cuando el
> especialista de DB publique el esquema real, los tests deberían seguir
> funcionando siempre que los campos del modelo `Comparable` referenciados
> por `valuation/queries.py` se conserven.
