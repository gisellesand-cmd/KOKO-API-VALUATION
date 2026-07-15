import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { KokoApiClient } from '../lib/api';
import { formatMxn, formatRange, formatPricePerM2 } from '../lib/format';
import { getStrings } from '../i18n';
import type {
  City,
  ConfidenceLevel,
  Locale,
  Operation,
  PropertyType,
  ValuationCompletedDetail,
  ValuationResponse,
  Zone,
} from '../types';

interface Props {
  apiUrl: string;
  locale: Locale;
  primaryColor?: string;
  onCompleted?: (detail: ValuationCompletedDetail) => void;
}

type Step = 'form' | 'result';

const CONFIDENCE_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  alta: { bg: '#ECFDF3', text: '#067647', dot: '#067647' },
  media: { bg: '#FEF6E7', text: '#B54708', dot: '#B54708' },
  baja: { bg: '#FFF4ED', text: '#C4320A', dot: '#C4320A' },
};

export function KokoValuationWidget({ apiUrl, locale, primaryColor, onCompleted }: Props) {
  const t = useMemo(() => getStrings(locale), [locale]);
  const client = useMemo(() => new KokoApiClient({ baseUrl: apiUrl }), [apiUrl]);

  const [step, setStep] = useState<Step>('form');
  const [cities, setCities] = useState<City[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [propertyTypes, setPropertyTypes] = useState<PropertyType[]>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [loadingZones, setLoadingZones] = useState(false);

  const [operation, setOperation] = useState<Operation>('venta');
  const [citySlug, setCitySlug] = useState('');
  const [zoneSlug, setZoneSlug] = useState('');
  const [propertyTypeSlug, setPropertyTypeSlug] = useState('');
  const [areaM2, setAreaM2] = useState('');
  const [bedrooms, setBedrooms] = useState('');
  const [bathrooms, setBathrooms] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ValuationResponse | null>(null);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const abortRef = useRef<AbortController | null>(null);
  const primary = primaryColor || '#C75B6A';

  useEffect(() => {
    const ac = new AbortController();
    (async () => {
      try {
        const [c, pt] = await Promise.all([
          client.getCities({ signal: ac.signal }),
          client.getPropertyTypes({ signal: ac.signal }),
        ]);
        setCities(c);
        setPropertyTypes(pt);
        if (pt.length > 0) setPropertyTypeSlug(pt[0].slug);
      } catch {
        // ignore abort
      } finally {
        setLoadingCatalog(false);
      }
    })();
    return () => ac.abort();
  }, [client]);

  useEffect(() => {
    if (!citySlug) {
      setZones([]);
      setZoneSlug('');
      return;
    }
    const ac = new AbortController();
    setLoadingZones(true);
    client
      .getZones(citySlug, { signal: ac.signal })
      .then((z) => {
        setZones(z);
        setZoneSlug('');
      })
      .catch(() => {})
      .finally(() => setLoadingZones(false));
    return () => ac.abort();
  }, [citySlug, client]);

  const validate = useCallback((): boolean => {
    const errs: Record<string, string> = {};
    if (!citySlug) errs.city = t.form.errors.required;
    if (!propertyTypeSlug) errs.propertyType = t.form.errors.required;
    const area = Number(areaM2);
    if (!areaM2) errs.area = t.form.errors.required;
    else if (isNaN(area)) errs.area = t.form.errors.areaInteger;
    else if (area <= 0) errs.area = t.form.errors.areaMin;
    else if (area > 10000) errs.area = t.form.errors.areaMax;
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }, [citySlug, propertyTypeSlug, areaM2, t]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError('');
      if (!validate()) return;

      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;
      setSubmitting(true);

      try {
        const res = await client.valuate(
          {
            city_slug: citySlug,
            ...(zoneSlug ? { zone_slug: zoneSlug } : {}),
            property_type_slug: propertyTypeSlug,
            operation,
            area_m2: Number(areaM2),
            bedrooms: bedrooms ? Number(bedrooms) : undefined,
            bathrooms: bathrooms ? Number(bathrooms) : undefined,
          },
          { signal: ac.signal },
        );
        setResult(res);
        setStep('result');
        onCompleted?.({
          confidence: res.confidence_level,
          comparables_count: res.comparables_count,
          geographic_scope: res.geographic_scope,
          range_mxn:
            res.price_min_mxn != null && res.price_median_mxn != null && res.price_max_mxn != null
              ? { min: res.price_min_mxn, median: res.price_median_mxn, max: res.price_max_mxn }
              : null,
          operation,
          city_slug: citySlug,
          zone_slug: zoneSlug,
          property_type_slug: propertyTypeSlug,
        });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : t.form.errors.generic;
        setError(msg);
      } finally {
        setSubmitting(false);
      }
    },
    [citySlug, zoneSlug, propertyTypeSlug, operation, areaM2, bedrooms, bathrooms, client, validate, onCompleted, t],
  );

  const handleNewEstimate = useCallback(() => {
    setStep('form');
    setResult(null);
    setError('');
  }, []);

  if (step === 'result' && result) {
    return (
      <ResultView
        result={result}
        t={t}
        primary={primary}
        onNewEstimate={handleNewEstimate}
      />
    );
  }

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <h2 style={styles.title}>{t.title}</h2>
        <p style={styles.subtitle}>{t.subtitle}</p>
      </div>

      <form onSubmit={handleSubmit} style={styles.form}>
        {/* Operation toggle */}
        <div style={styles.toggleGroup}>
          {(['venta', 'renta'] as Operation[]).map((op) => (
            <button
              key={op}
              type="button"
              onClick={() => setOperation(op)}
              style={{
                ...styles.toggleBtn,
                ...(operation === op
                  ? { backgroundColor: primary, color: '#fff', borderColor: primary }
                  : {}),
              }}
            >
              {t.form.operation[op]}
            </button>
          ))}
        </div>

        {/* City */}
        <Field label={t.form.city.label} error={fieldErrors.city}>
          <select
            value={citySlug}
            onChange={(e) => setCitySlug(e.target.value)}
            style={styles.select}
            disabled={loadingCatalog}
          >
            <option value="">
              {loadingCatalog ? t.form.city.loading : t.form.city.placeholder}
            </option>
            {cities.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>

        {/* Zone */}
        <Field label={t.form.zone.label}>
          <select
            value={zoneSlug}
            onChange={(e) => setZoneSlug(e.target.value)}
            style={styles.select}
            disabled={!citySlug || loadingZones}
          >
            <option value="">
              {loadingZones
                ? t.form.zone.loading
                : !citySlug
                  ? t.form.zone.placeholderDisabled
                  : t.form.zone.placeholder}
            </option>
            {zones.map((z) => (
              <option key={z.slug} value={z.slug}>
                {z.name}
              </option>
            ))}
          </select>
        </Field>

        {/* Property type */}
        <Field label={t.form.propertyType.label} error={fieldErrors.propertyType}>
          <select
            value={propertyTypeSlug}
            onChange={(e) => setPropertyTypeSlug(e.target.value)}
            style={styles.select}
            disabled={loadingCatalog}
          >
            {loadingCatalog && <option>{t.form.propertyType.loading}</option>}
            {propertyTypes.map((pt) => (
              <option key={pt.slug} value={pt.slug}>
                {pt.name}
              </option>
            ))}
          </select>
        </Field>

        {/* Area */}
        <Field label={t.form.area.label} error={fieldErrors.area}>
          <div style={styles.inputWithSuffix}>
            <input
              type="number"
              value={areaM2}
              onChange={(e) => setAreaM2(e.target.value)}
              placeholder={t.form.area.placeholder}
              style={{ ...styles.input, paddingRight: 48 }}
              min={1}
              max={10000}
              step="any"
            />
            <span style={styles.suffix}>{t.form.area.suffix}</span>
          </div>
        </Field>

        {/* Bedrooms & Bathrooms */}
        <div style={styles.row}>
          <Field label={t.form.bedrooms.label}>
            <input
              type="number"
              value={bedrooms}
              onChange={(e) => setBedrooms(e.target.value)}
              style={styles.input}
              min={0}
              max={20}
            />
          </Field>
          <Field label={t.form.bathrooms.label}>
            <input
              type="number"
              value={bathrooms}
              onChange={(e) => setBathrooms(e.target.value)}
              style={styles.input}
              min={0}
              max={20}
            />
          </Field>
        </div>

        {error && <p style={styles.errorBanner}>{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          style={{
            ...styles.submitBtn,
            backgroundColor: submitting ? '#9CA3AF' : primary,
          }}
        >
          {submitting ? (
            <span style={styles.spinnerWrap}>
              <Spinner />
              {t.form.submit.loading}
            </span>
          ) : (
            t.form.submit.idle
          )}
        </button>
      </form>
    </div>
  );
}

function ResultView({
  result,
  t,
  primary,
  onNewEstimate,
}: {
  result: ValuationResponse;
  t: ReturnType<typeof getStrings>;
  primary: string;
  onNewEstimate: () => void;
}) {
  const isInsufficient = result.confidence_level === 'insuficiente';

  if (isInsufficient) {
    return (
      <div style={styles.card}>
        <div style={{ textAlign: 'center' as const, padding: '32px 16px' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>📊</div>
          <h3 style={{ ...styles.title, fontSize: 18 }}>{t.result.insufficient.title}</h3>
          <p style={{ ...styles.subtitle, marginBottom: 24 }}>{result.methodology_note}</p>
          <button onClick={onNewEstimate} style={{ ...styles.submitBtn, backgroundColor: primary }}>
            {t.result.ctaNew}
          </button>
        </div>
      </div>
    );
  }

  const conf = CONFIDENCE_COLORS[result.confidence_level] || CONFIDENCE_COLORS.media;
  const scope = result.geographic_scope as string;
  const scopeLabel = scope === 'zone' || scope === 'zona' ? 'la zona' : 'la ciudad';

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 13,
            fontWeight: 600,
            padding: '4px 12px',
            borderRadius: 20,
            backgroundColor: conf.bg,
            color: conf.text,
          }}
        >
          <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: conf.dot }} />
          {t.result.confidence[result.confidence_level as Exclude<ConfidenceLevel, 'insuficiente'>]}
        </span>
      </div>

      {result.price_min_mxn != null && result.price_max_mxn != null && (
        <div style={{ textAlign: 'center' as const, padding: '16px 0' }}>
          <p style={{ fontSize: 13, color: '#5A5A5A', margin: '0 0 4px' }}>Rango estimado</p>
          <p style={{ fontSize: 26, fontWeight: 700, color: '#2D2D2D', margin: 0 }}>
            {formatRange(result.price_min_mxn, result.price_max_mxn)}
          </p>
          {result.price_median_mxn != null && (
            <p style={{ fontSize: 15, color: '#5A5A5A', margin: '4px 0 0' }}>
              Mediana: {formatMxn(result.price_median_mxn)}
            </p>
          )}
        </div>
      )}

      {result.price_per_m2_median != null && (
        <div style={styles.statRow}>
          <span style={{ color: '#5A5A5A', fontSize: 13 }}>{t.result.pricePerM2}</span>
          <span style={{ fontWeight: 600, fontSize: 14 }}>
            {formatPricePerM2(result.price_per_m2_median)}
          </span>
        </div>
      )}

      <div style={styles.statRow}>
        <span style={{ color: '#5A5A5A', fontSize: 13 }}>Comparables</span>
        <span style={{ fontWeight: 600, fontSize: 14 }}>{result.comparables_count}</span>
      </div>

      <p style={{ fontSize: 12, color: '#5A5A5A', margin: '12px 0 0', lineHeight: 1.5 }}>
        {t.result.basedOn(result.comparables_count, scopeLabel)}
      </p>

      <p style={{ fontSize: 11, color: '#9CA3AF', margin: '8px 0 0', fontStyle: 'italic' }}>
        {result.disclaimer}
      </p>

      <button
        onClick={onNewEstimate}
        style={{
          ...styles.submitBtn,
          backgroundColor: 'transparent',
          color: primary,
          border: `1.5px solid ${primary}`,
          marginTop: 20,
        }}
      >
        {t.result.ctaNew}
      </button>
    </div>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div style={styles.field}>
      <label style={styles.label}>{label}</label>
      {children}
      {error && <span style={styles.fieldError}>{error}</span>}
    </div>
  );
}

function Spinner() {
  return (
    <svg
      width={16}
      height={16}
      viewBox="0 0 16 16"
      fill="none"
      style={{ animation: 'koko-spin 0.8s linear infinite' }}
    >
      <circle cx={8} cy={8} r={6} stroke="currentColor" strokeWidth={2} opacity={0.3} />
      <path
        d="M14 8a6 6 0 0 0-6-6"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
      />
    </svg>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    backgroundColor: '#fff',
    borderRadius: 14,
    boxShadow: '0 4px 24px -8px rgba(15,23,42,0.12)',
    padding: '28px 24px',
    maxWidth: 480,
    width: '100%',
    margin: '0 auto',
  },
  header: {
    marginBottom: 20,
  },
  title: {
    fontSize: 20,
    fontWeight: 700,
    color: '#2D2D2D',
    margin: '0 0 4px',
  },
  subtitle: {
    fontSize: 14,
    color: '#5A5A5A',
    margin: 0,
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  toggleGroup: {
    display: 'flex',
    gap: 0,
    borderRadius: 8,
    overflow: 'hidden',
    border: '1.5px solid #E0DAD2',
  },
  toggleBtn: {
    flex: 1,
    padding: '10px 0',
    border: 'none',
    backgroundColor: '#fff',
    color: '#5A5A5A',
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    flex: 1,
  },
  label: {
    fontSize: 13,
    fontWeight: 500,
    color: '#2D2D2D',
  },
  select: {
    padding: '10px 12px',
    borderRadius: 8,
    border: '1.5px solid #E0DAD2',
    fontSize: 14,
    color: '#2D2D2D',
    backgroundColor: '#fff',
    appearance: 'auto' as React.CSSProperties['appearance'],
    width: '100%',
  },
  input: {
    padding: '10px 12px',
    borderRadius: 8,
    border: '1.5px solid #E0DAD2',
    fontSize: 14,
    color: '#2D2D2D',
    width: '100%',
  },
  inputWithSuffix: {
    position: 'relative',
  },
  suffix: {
    position: 'absolute',
    right: 12,
    top: '50%',
    transform: 'translateY(-50%)',
    fontSize: 13,
    color: '#9CA3AF',
    pointerEvents: 'none',
  },
  row: {
    display: 'flex',
    gap: 12,
  },
  submitBtn: {
    padding: '12px 20px',
    borderRadius: 8,
    border: 'none',
    color: '#fff',
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    width: '100%',
    transition: 'opacity 0.15s',
  },
  errorBanner: {
    padding: '10px 12px',
    borderRadius: 8,
    backgroundColor: '#FEF3F2',
    color: '#B42318',
    fontSize: 13,
    margin: 0,
  },
  fieldError: {
    fontSize: 12,
    color: '#B42318',
  },
  spinnerWrap: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
  },
  statRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 0',
    borderBottom: '1px solid #EDE8E0',
  },
};
