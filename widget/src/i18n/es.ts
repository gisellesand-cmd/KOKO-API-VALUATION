export const es = {
  title: 'Estimador de valor KOKO™',
  subtitle: 'Recibe un rango de valor basado en anuncios reales de la zona.',
  form: {
    operation: {
      label: 'Operación',
      venta: 'Venta',
      renta: 'Renta',
    },
    city: {
      label: 'Ciudad',
      placeholder: 'Selecciona una ciudad',
      loading: 'Cargando ciudades…',
    },
    zone: {
      label: 'Zona o colonia',
      placeholder: 'Selecciona una zona',
      placeholderDisabled: 'Primero elige una ciudad',
      loading: 'Cargando zonas…',
    },
    propertyType: {
      label: 'Tipo de propiedad',
      loading: 'Cargando tipos…',
    },
    area: {
      label: 'Área construida',
      suffix: 'm²',
      placeholder: 'Ej. 120',
    },
    bedrooms: {
      label: 'Recámaras (opcional)',
    },
    bathrooms: {
      label: 'Baños (opcional)',
    },
    submit: {
      idle: 'Estimar valor',
      loading: 'Calculando…',
    },
    errors: {
      required: 'Este campo es obligatorio',
      areaMin: 'El área debe ser mayor a 0 m²',
      areaMax: 'El área parece demasiado grande. Verifica.',
      areaInteger: 'Ingresa solo números',
      network: 'No pudimos conectar con el servidor. Reintenta.',
      generic: 'Algo salió mal. Intenta de nuevo en unos segundos.',
    },
  },
  result: {
    confidence: {
      alta: 'Confianza alta',
      media: 'Confianza media',
      baja: 'Confianza baja',
    },
    basedOn: (n: number, scope: string): string =>
      `Basado en ${n} ${n === 1 ? 'anuncio real' : 'anuncios reales'} en ${scope}`,
    pricePerM2: 'Precio por m² (mediana)',
    insufficient: {
      title: 'Datos insuficientes',
      ctaTalk: 'Hablar con un agente KOKO',
    },
    ctaPublish: 'Publicar mi propiedad en KOKO',
    ctaNew: 'Hacer otra estimación',
  },
  errors: {
    boundary: 'El widget tuvo un problema inesperado. Recarga la página.',
  },
} as const;
