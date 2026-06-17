# @koko/ui — Sistema de diseño para el widget de valuación

Biblioteca de componentes, tokens y patrones para el widget de valuación de propiedades de **KOKO MLS**. Construida sobre TypeScript, React 18, Tailwind CSS 3, [class-variance-authority](https://cva.style/) y primitivas de [Radix UI](https://www.radix-ui.com/).

---

## Filosofía de diseño

KOKO es una marca **premium pero accesible** dentro del segmento inmobiliario mexicano. El sistema visual toma referencias de jugadores globales como Compass y Zillow, pero los simplifica para el contexto local: una paleta de verdes profundos (esmeralda) acentuada con un dorado cálido, tipografía display moderna y un ritmo de espaciado generoso. **El 70% del tráfico es móvil**, por lo que cada componente se diseña primero para pantallas estrechas y luego se enriquece en breakpoints mayores.

El principio rector del producto es **"cero datos inventados"**. Cuando el motor de valuación no tiene comparables suficientes, el widget lo declara abiertamente con un badge de *confianza insuficiente* en lugar de fabricar una cifra. Esa honestidad da forma al lenguaje visual: los *empty states* son explícitos y nunca disfrazados de placeholders; cada cifra está acompañada de evidencia (número de comparables, rango, antigüedad de los datos); el sistema de color de confianza —`alta`, `media`, `baja`, `insuficiente`— es de primera clase, no un afterthought.

La **jerarquía tipográfica** pone el número al centro. La escala `display-sm/md/lg` (Plus Jakarta Sans, peso 700, tracking negativo) se reserva exclusivamente para la cifra de valuación o el rango estimado. Todo lo demás —labels, ayudas, metadatos— vive en Inter a tamaños menores. La cifra debe sentirse como la conclusión de un argumento, no como un número decorativo.

El **tono** es respaldado por datos, nunca pidiendo disculpas. Cuando hay confianza alta, el widget afirma. Cuando es insuficiente, explica qué falta (cuántos comparables hay, qué se necesita) y propone siguiente paso (ampliar zona, ajustar parámetros, hablar con un asesor). En ningún caso una cifra inventada llena el vacío.

---

## Instalación

```bash
pnpm add @koko/ui
```

Y en tu `tailwind.config.js`:

```js
module.exports = {
  presets: [require('@koko/ui/tailwind.preset')],
  content: [
    './src/**/*.{ts,tsx}',
    './node_modules/@koko/ui/**/*.{ts,tsx}',
  ],
};
```

El preset trae colores, tipografía, espaciado, radios, sombras, z-index, breakpoints y curvas de animación. No necesitas declarar nada adicional en `theme.extend` salvo lo específico de tu app.

---

## Tabla de tokens

### Colores — marca

| Token             | Hex       | Uso                                                |
| ----------------- | --------- | -------------------------------------------------- |
| `koko-primary`     | `#0F5132` | Botón primario, focus ring, links                  |
| `koko-primary-dark`| `#0A3D24` | Hover/active del primario                          |
| `koko-primary-light`| `#1A7A4F`| Estados sutiles, fondos tintados                   |
| `koko-accent`      | `#D4A047` | Highlights premium, badges destacados              |

### Colores — confianza (cero datos inventados)

| Nivel           | Base      | Background | Texto     | Significado            |
| --------------- | --------- | ---------- | --------- | ---------------------- |
| `alta`          | `#16A34A` | `#DCFCE7`  | `#14532D` | ≥ 8 comparables        |
| `media`         | `#F59E0B` | `#FEF3C7`  | `#78350F` | 4–7 comparables        |
| `baja`          | `#F97316` | `#FFEDD5`  | `#7C2D12` | 1–3 comparables        |
| `insuficiente`  | `#71717A` | `#F4F4F5`  | `#3F3F46` | 0 comparables          |

### Colores — semánticos

| Token       | Light     | Base      | Dark      |
| ----------- | --------- | --------- | --------- |
| `success`   | `#DCFCE7` | `#16A34A` | `#15803D` |
| `warning`   | `#FEF3C7` | `#F59E0B` | `#B45309` |
| `danger`    | `#FEE2E2` | `#DC2626` | `#B91C1C` |
| `info`      | `#DBEAFE` | `#2563EB` | `#1D4ED8` |

### Tipografía — tamaños

| Token         | Tamaño    | Line-height | Uso                                  |
| ------------- | --------- | ----------- | ------------------------------------ |
| `xs`          | 0.75rem   | 1rem        | Captions, microcopy                  |
| `sm`          | 0.875rem  | 1.25rem     | Ayudas, badges                       |
| `base`        | 1rem      | 1.5rem      | Body por defecto                     |
| `lg`          | 1.125rem  | 1.75rem     | Subtítulos                           |
| `xl`          | 1.25rem   | 1.75rem     | Titulares menores                    |
| `2xl`         | 1.5rem    | 2rem        | Section headings                     |
| `3xl`         | 1.875rem  | 2.25rem     | Page headings                        |
| `4xl`         | 2.25rem   | 2.5rem      | Hero secundario                      |
| `5xl`         | 3rem      | 1.1         | Hero                                 |
| `display-sm`  | 2.5rem    | 1.1         | **Cifra de valuación (móvil)**       |
| `display-md`  | 3.5rem    | 1.05        | **Cifra de valuación (tablet)**      |
| `display-lg`  | 4.5rem    | 1.0         | **Cifra de valuación (desktop)**     |

### Espaciado (base 4px)

| Token | Valor | Token | Valor |
| ----- | ----- | ----- | ----- |
| `0`   | 0     | `6`   | 24px  |
| `1`   | 4px   | `8`   | 32px  |
| `2`   | 8px   | `10`  | 40px  |
| `3`   | 12px  | `12`  | 48px  |
| `4`   | 16px  | `16`  | 64px  |
| `5`   | 20px  | `20`  | 80px  |
|       |       | `24`  | 96px  |

### Border radius

| Token   | Valor   | Uso                              |
| ------- | ------- | -------------------------------- |
| `none`  | 0       | Tablas, divisores                |
| `xs`    | 2px     | Chips muy compactos              |
| `sm`    | 4px     | Inputs, buttons compactos        |
| `md`    | 8px     | Buttons, cards densos            |
| `lg`    | 12px    | Cards, modales                   |
| `xl`    | 16px    | Containers prominentes           |
| `2xl`   | 24px    | Hero panels                      |
| `full`  | 9999px  | Avatares, pills                  |

### Sombras (tintadas en `koko-primary`)

| Token   | Uso                                              |
| ------- | ------------------------------------------------ |
| `xs`    | Bordes elevados sutiles                          |
| `sm`    | Cards en reposo                                  |
| `md`    | Cards en hover, dropdowns                        |
| `lg`    | Popovers, modales pequeños                       |
| `xl`    | Modales grandes, sheets                          |
| `focus` | Ring de focus accesible (3px)                    |
| `none`  | Sin elevación                                    |

---

## Anatomía de un componente: Button

```tsx
import { Button } from '@koko/ui';

<Button variant="primary" size="md" onClick={handleSubmit}>
  Calcular valuación
</Button>
```

**Variantes:** `primary` · `secondary` · `ghost` · `outline` · `danger`
**Tamaños:** `sm` (32px) · `md` (40px) · `lg` (48px) · `xl` (56px, móvil hero)

Todos los componentes interactivos siguen el patrón CVA:

```ts
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@koko/ui';

const buttonVariants = cva(
  'inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:shadow-focus disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-koko-primary text-text-inverse hover:bg-koko-primary-dark',
        secondary: 'bg-surface-subtle text-text-primary hover:bg-gray-200',
        // ...
      },
      size: {
        sm: 'h-8 px-3 text-sm rounded-sm',
        md: 'h-10 px-4 text-base rounded-md',
        lg: 'h-12 px-6 text-lg rounded-md',
        xl: 'h-14 px-8 text-lg rounded-lg',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
);
```

**`asChild` + Slot** — Todos los componentes "envolventes" aceptan `asChild` para delegar el render al hijo (ver `@radix-ui/react-slot`). Esto permite componer un `<Button>` con un `<Link>` de Next.js sin perder accesibilidad ni estilos:

```tsx
<Button asChild variant="ghost">
  <Link href="/comparables">Ver comparables</Link>
</Button>
```

---

## Uso desde el widget

Esta librería es consumida por el branch **`feature/frontend-widget`** del monorepo. El widget no implementa primitivas: compone **patrones** —`PropertyTypePicker`, `ConfidenceMeter`, `ResultEmptyState`, etc.— que viven en `ui/patterns/` y a su vez se construyen sobre los componentes base de `ui/components/`.

Regla de oro: **si vas a usarlo dos veces, vive aquí**. Si es lógica de negocio o orquestación de una pantalla específica, vive en el widget.

---

## Accesibilidad

- **Contraste AA mínimo** en toda combinación `text-*` sobre `surface-*` o `bg-confidence-*`. Las combinaciones se validan contra WCAG 2.1.
- **Focus visible**: anillo de 3px usando el token `shadow.focus` (`rgba(15, 81, 50, 0.25)`). Nunca usamos `outline: none` sin reemplazo.
- **Primitivas Radix UI** aportan roles ARIA, manejo de teclado, focus trap y *escape hatches* probados (Select, Tooltip, Collapsible, RadioGroup, ToggleGroup, Label).
- **Tap targets ≥ 44×44px** en componentes interactivos clave (tamaño `md` y superiores). El tamaño `sm` se reserva para escritorio o densidad informativa.
- **`prefers-reduced-motion`**: las transiciones del sistema honran el media query del usuario; las animaciones decorativas se desactivan, las funcionales se reducen a fades cortos.
- **HTML semántico** y labels asociadas (`<label htmlFor>` o `aria-labelledby`) en todos los controles de formulario. Nunca placeholders como label.

---

## Estructura

```
ui/
├── package.json
├── tsconfig.json
├── tailwind.preset.cjs        ← Preset Tailwind para consumidores
├── index.ts                   ← Barrel raíz
├── README.md
│
├── tokens/                    ← Tokens de diseño (fuente única de verdad)
│   ├── colors.ts
│   ├── typography.ts
│   ├── spacing.ts
│   ├── radii.ts
│   ├── shadows.ts
│   ├── zIndex.ts
│   ├── breakpoints.ts
│   ├── motion.ts
│   └── index.ts
│
├── utils/                     ← Helpers (cn, etc.)
│   ├── cn.ts
│   └── index.ts
│
├── components/                ← Primitivas (Button, Input, Badge, Card…)
│   └── index.ts
│
├── patterns/                  ← Composiciones de dominio
│   └── index.ts               (PropertyTypePicker, ConfidenceMeter,
│                               ResultEmptyState, …)
│
├── icons/                     ← Icon set (24px stroke)
│   └── index.ts
│
└── storybook/                 ← Documentación viva
```
