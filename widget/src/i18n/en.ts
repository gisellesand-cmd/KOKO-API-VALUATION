import type { es } from './es';

export const en = {
  title: 'KOKO value estimator',
  subtitle: 'Get a value range based on real listings in the area.',
  form: {
    operation: {
      label: 'Operation',
      venta: 'Sale',
      renta: 'Rent',
    },
    city: {
      label: 'City',
      placeholder: 'Select a city',
      loading: 'Loading cities…',
    },
    zone: {
      label: 'Zone or neighborhood',
      placeholder: 'Select a zone',
      placeholderDisabled: 'First choose a city',
      loading: 'Loading zones…',
    },
    propertyType: {
      label: 'Property type',
      loading: 'Loading types…',
    },
    area: {
      label: 'Built area',
      suffix: 'm²',
      placeholder: 'E.g. 120',
    },
    bedrooms: {
      label: 'Bedrooms (optional)',
    },
    bathrooms: {
      label: 'Bathrooms (optional)',
    },
    submit: {
      idle: 'Estimate value',
      loading: 'Calculating…',
    },
    errors: {
      required: 'This field is required',
      areaMin: 'Area must be greater than 0 m²',
      areaMax: 'That area seems too large. Please double-check.',
      areaInteger: 'Enter numbers only',
      network: 'We could not reach the server. Please retry.',
      generic: 'Something went wrong. Please try again in a few seconds.',
    },
  },
  result: {
    confidence: {
      alta: 'High confidence',
      media: 'Medium confidence',
      baja: 'Low confidence',
    },
    basedOn: (n: number, scope: string): string =>
      `Based on ${n} real ${n === 1 ? 'listing' : 'listings'} in ${scope}`,
    pricePerM2: 'Price per m² (median)',
    insufficient: {
      title: 'Not enough data',
      ctaTalk: 'Talk to a KOKO agent',
    },
    ctaPublish: 'List my property on KOKO',
    ctaNew: 'Run another estimate',
  },
  errors: {
    boundary: 'The widget hit an unexpected problem. Please reload the page.',
  },
} satisfies typeof es;
