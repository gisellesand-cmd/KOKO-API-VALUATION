const PLACEHOLDER = '—';

function isFinitNumber(value: number): boolean {
  return typeof value === 'number' && Number.isFinite(value);
}

function trimZeroDecimal(value: number, digits: number): string {
  const fixed = value.toFixed(digits);
  return fixed.replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1');
}

export function formatMxn(
  value: number,
  opts: { compact?: boolean } = {},
): string {
  if (!isFinitNumber(value)) return PLACEHOLDER;
  const compact = opts.compact !== false;
  const abs = Math.abs(value);

  if (compact && abs >= 1_000_000) {
    const millions = value / 1_000_000;
    const num = trimZeroDecimal(millions, 1);
    return `$${num} M MXN`;
  }

  if (compact && abs >= 1_000) {
    const thousands = Math.round(value / 1_000);
    const num = new Intl.NumberFormat('es-MX').format(thousands);
    return `$${num} mil MXN`;
  }

  const formatted = new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    maximumFractionDigits: 0,
  }).format(value);
  const cleaned = formatted.replace(/[.,]00$/, '');
  return `${cleaned} MXN`;
}

export function formatRange(min: number, max: number): string {
  if (!isFinitNumber(min) || !isFinitNumber(max)) return PLACEHOLDER;
  return `${formatMxn(min)} – ${formatMxn(max)}`;
}

export function formatArea(m2: number): string {
  if (!isFinitNumber(m2)) return PLACEHOLDER;
  return `${new Intl.NumberFormat('es-MX').format(m2)} m²`;
}

export function formatPricePerM2(value: number): string {
  if (!isFinitNumber(value)) return PLACEHOLDER;
  const num = new Intl.NumberFormat('es-MX', {
    maximumFractionDigits: 0,
  }).format(value);
  return `${num} MXN/m²`;
}

export function formatInteger(value: number): string {
  if (!isFinitNumber(value)) return PLACEHOLDER;
  return new Intl.NumberFormat('es-MX').format(value);
}
