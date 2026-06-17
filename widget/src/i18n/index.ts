import { es } from './es';
import { en } from './en';
import type { Locale } from '../types';

export type StringTable = typeof es;

export function getStrings(locale: Locale): StringTable {
  return locale === 'en' ? (en as unknown as StringTable) : es;
}

export { es, en };
