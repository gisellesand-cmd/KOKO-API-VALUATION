export type Locale = 'es' | 'en';

export type Operation = 'venta' | 'renta';

export type ConfidenceLevel = 'alta' | 'media' | 'baja' | 'insuficiente';

export type GeographicScope = 'zona' | 'ciudad' | 'nacional';

export interface City {
  slug: string;
  name: string;
}

export interface Zone {
  slug: string;
  name: string;
}

export interface PropertyType {
  slug: string;
  name: string;
}

export interface ValuationRequest {
  city_slug: string;
  zone_slug: string;
  property_type_slug: string;
  operation: Operation;
  area_m2: number;
  bedrooms?: number;
  bathrooms?: number;
}

export interface ValuationResponse {
  confidence_level: ConfidenceLevel;
  comparables_count: number;
  geographic_scope: GeographicScope;
  price_min_mxn: number | null;
  price_median_mxn: number | null;
  price_max_mxn: number | null;
  price_per_m2_median: number | null;
  methodology_note: string;
  disclaimer: string;
}

export interface ValuationCompletedDetail {
  confidence: ConfidenceLevel;
  comparables_count: number;
  geographic_scope: GeographicScope;
  range_mxn: { min: number; median: number; max: number } | null;
  operation: Operation;
  city_slug: string;
  zone_slug: string;
  property_type_slug: string;
}

export interface MountOptions {
  apiUrl: string;
  primaryColor?: string;
  locale?: Locale;
  onCompleted?: (detail: ValuationCompletedDetail) => void;
}
