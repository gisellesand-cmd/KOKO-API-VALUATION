import React from 'react';
import { KokoValuationWidget } from './KokoValuationWidget';
import type { Locale } from '../types';

interface Props {
  apiUrl: string;
  locale: Locale;
}

export function LandingPage({ apiUrl, locale }: Props) {
  return (
    <div style={pageStyles.wrapper}>
      <nav style={pageStyles.nav}>
        <div style={pageStyles.logoWrap}>
          <span style={pageStyles.logo}>KOKO</span>
          <span style={pageStyles.tm}>™</span>
          <div style={pageStyles.taglineBlock}>
            <span style={pageStyles.taglineLine}>MEXICO</span>
            <span style={pageStyles.taglineLine}>LISTING</span>
            <span style={pageStyles.taglineLine}>SERVICES</span>
          </div>
        </div>
      </nav>

      <header style={pageStyles.hero}>
        <h1 style={pageStyles.heroTitle}>
          ¿Cuánto vale tu propiedad?
        </h1>
        <p style={pageStyles.heroSubtitle}>
          Obtén una estimación basada en datos reales de mercado.
          Sin registros, sin esperas. Datos de anuncios actuales en tu zona.
        </p>
      </header>

      <main style={pageStyles.main}>
        <KokoValuationWidget apiUrl={apiUrl} locale={locale} />
      </main>

      <section style={pageStyles.features}>
        <div style={pageStyles.featureCard}>
          <div style={pageStyles.featureIcon}>📊</div>
          <h3 style={pageStyles.featureTitle}>Datos reales</h3>
          <p style={pageStyles.featureDesc}>
            Comparamos con anuncios actuales de Inmuebles24 y otras fuentes de tu zona.
          </p>
        </div>
        <div style={pageStyles.featureCard}>
          <div style={pageStyles.featureIcon}>🎯</div>
          <h3 style={pageStyles.featureTitle}>Transparente</h3>
          <p style={pageStyles.featureDesc}>
            Te decimos cuántos comparables usamos y el nivel de confianza del resultado.
          </p>
        </div>
        <div style={pageStyles.featureCard}>
          <div style={pageStyles.featureIcon}>⚡</div>
          <h3 style={pageStyles.featureTitle}>Instantáneo</h3>
          <p style={pageStyles.featureDesc}>
            Resultados en segundos. Sin necesidad de registro ni datos personales.
          </p>
        </div>
      </section>

      <footer style={pageStyles.footer}>
        <p style={pageStyles.footerText}>
          KOKO™ Mexico Listing Services — Referencia de mercado, no avalúo profesional.
        </p>
      </footer>
    </div>
  );
}

const pageStyles: Record<string, React.CSSProperties> = {
  wrapper: {
    minHeight: '100vh',
    backgroundColor: '#F0EBE3',
    fontFamily: "'Poppins', system-ui, -apple-system, sans-serif",
  },
  nav: {
    display: 'flex',
    alignItems: 'center',
    padding: '16px 24px',
    backgroundColor: '#fff',
    borderBottom: '1px solid #E0DAD2',
  },
  logoWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  logo: {
    fontSize: 28,
    fontWeight: 800,
    color: '#2D2D2D',
    letterSpacing: 2,
  },
  tm: {
    fontSize: 11,
    fontWeight: 600,
    color: '#2D2D2D',
    verticalAlign: 'super',
    marginRight: 10,
  },
  taglineBlock: {
    display: 'flex',
    flexDirection: 'column' as const,
    lineHeight: 1.1,
  },
  taglineLine: {
    fontSize: 8,
    fontWeight: 500,
    color: '#2D2D2D',
    letterSpacing: 2.5,
  },
  hero: {
    textAlign: 'center' as const,
    padding: '48px 24px 16px',
    maxWidth: 600,
    margin: '0 auto',
  },
  heroTitle: {
    fontSize: 32,
    fontWeight: 800,
    color: '#2D2D2D',
    margin: '0 0 12px',
    lineHeight: 1.2,
  },
  heroSubtitle: {
    fontSize: 16,
    color: '#5A5A5A',
    margin: 0,
    lineHeight: 1.6,
  },
  main: {
    padding: '24px 16px 48px',
    maxWidth: 520,
    margin: '0 auto',
  },
  features: {
    display: 'flex',
    justifyContent: 'center',
    gap: 20,
    padding: '0 24px 48px',
    maxWidth: 800,
    margin: '0 auto',
    flexWrap: 'wrap' as const,
  },
  featureCard: {
    flex: '1 1 200px',
    maxWidth: 240,
    textAlign: 'center' as const,
    padding: '24px 16px',
    backgroundColor: '#fff',
    borderRadius: 14,
    boxShadow: '0 2px 12px -4px rgba(45,45,45,0.08)',
  },
  featureIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  featureTitle: {
    fontSize: 15,
    fontWeight: 700,
    color: '#2D2D2D',
    margin: '0 0 4px',
  },
  featureDesc: {
    fontSize: 13,
    color: '#5A5A5A',
    margin: 0,
    lineHeight: 1.5,
  },
  footer: {
    borderTop: '1px solid #E0DAD2',
    padding: '20px 24px',
    textAlign: 'center' as const,
  },
  footerText: {
    fontSize: 12,
    color: '#8A8A8A',
    margin: 0,
  },
};
