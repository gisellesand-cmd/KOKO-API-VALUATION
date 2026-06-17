import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind class names with conflict resolution.
 *
 * Combines clsx (for conditional / array / object class composition) with
 * tailwind-merge (for resolving conflicts like `px-2 px-4` → `px-4`).
 *
 * @example
 *   cn('px-2', condition && 'px-4', { 'text-red-500': isError });
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
