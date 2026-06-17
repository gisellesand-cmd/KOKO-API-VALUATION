import type {
  City,
  PropertyType,
  ValuationRequest,
  ValuationResponse,
  Zone,
} from '../types';

export type KokoApiErrorCode = 'timeout' | 'network' | 'http' | 'aborted';

export class KokoApiError extends Error {
  public readonly status: number;
  public readonly code: KokoApiErrorCode;
  public readonly body?: unknown;

  constructor(args: {
    status: number;
    message: string;
    code: KokoApiErrorCode;
    body?: unknown;
  }) {
    super(args.message);
    this.name = 'KokoApiError';
    this.status = args.status;
    this.code = args.code;
    this.body = args.body;
  }
}

export interface KokoApiClientOptions {
  baseUrl: string;
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
}

interface RequestOptions {
  signal?: AbortSignal;
}

const RETRY_BACKOFF_MS = 400;

function joinUrl(baseUrl: string, path: string): string {
  const left = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  const right = path.startsWith('/') ? path : `/${path}`;
  return `${left}${right}`;
}

function linkSignals(
  controller: AbortController,
  external?: AbortSignal,
): () => void {
  if (!external) return () => {};
  if (external.aborted) {
    controller.abort(external.reason);
    return () => {};
  }
  const onAbort = () => controller.abort(external.reason);
  external.addEventListener('abort', onAbort);
  return () => external.removeEventListener('abort', onAbort);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export class KokoApiClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly fetchImpl: typeof fetch;

  constructor(options: KokoApiClientOptions) {
    this.baseUrl = options.baseUrl;
    this.timeoutMs = options.timeoutMs ?? 8000;
    this.fetchImpl =
      options.fetchImpl ?? globalThis.fetch.bind(globalThis);
  }

  getCities(opts: RequestOptions = {}): Promise<City[]> {
    return this.request<City[]>('/v1/cities', { method: 'GET' }, opts);
  }

  getZones(citySlug: string, opts: RequestOptions = {}): Promise<Zone[]> {
    const encoded = encodeURIComponent(citySlug);
    return this.request<Zone[]>(
      `/v1/cities/${encoded}/zones`,
      { method: 'GET' },
      opts,
    );
  }

  getPropertyTypes(opts: RequestOptions = {}): Promise<PropertyType[]> {
    return this.request<PropertyType[]>(
      '/v1/property-types',
      { method: 'GET' },
      opts,
    );
  }

  valuate(
    req: ValuationRequest,
    opts: RequestOptions = {},
  ): Promise<ValuationResponse> {
    return this.request<ValuationResponse>(
      '/v1/valuation',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      },
      opts,
    );
  }

  private async request<T>(
    path: string,
    init: RequestInit,
    opts: RequestOptions,
  ): Promise<T> {
    const url = joinUrl(this.baseUrl, path);
    const headers = new Headers(init.headers);
    headers.set('Accept', 'application/json');

    const attempt = async (isRetry: boolean): Promise<T> => {
      const controller = new AbortController();
      const unlink = linkSignals(controller, opts.signal);
      const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

      try {
        const res = await this.fetchImpl(url, {
          ...init,
          headers,
          signal: controller.signal,
        });

        if (res.ok) {
          if (res.status === 204) return undefined as T;
          const body = await parseBody(res);
          return body as T;
        }

        const body = await parseBody(res);
        const message =
          (typeof body === 'object' &&
            body !== null &&
            'detail' in body &&
            typeof (body as { detail: unknown }).detail === 'string' &&
            (body as { detail: string }).detail) ||
          `Request failed with status ${res.status}`;

        if (res.status >= 500 && !isRetry) {
          await sleep(RETRY_BACKOFF_MS);
          return attempt(true);
        }

        throw new KokoApiError({
          status: res.status,
          message,
          code: 'http',
          body,
        });
      } catch (err) {
        if (err instanceof KokoApiError) throw err;

        const aborted =
          (err instanceof DOMException && err.name === 'AbortError') ||
          (err as { name?: string })?.name === 'AbortError';

        if (aborted) {
          if (opts.signal?.aborted) {
            throw new KokoApiError({
              status: 0,
              message: 'Request was aborted',
              code: 'aborted',
            });
          }
          throw new KokoApiError({
            status: 0,
            message: 'Request timed out',
            code: 'timeout',
          });
        }

        if (err instanceof TypeError) {
          if (!isRetry) {
            await sleep(RETRY_BACKOFF_MS);
            return attempt(true);
          }
          throw new KokoApiError({
            status: 0,
            message: err.message || 'Network error',
            code: 'network',
          });
        }

        throw new KokoApiError({
          status: 0,
          message: (err as Error)?.message ?? 'Unknown error',
          code: 'network',
        });
      } finally {
        clearTimeout(timeoutId);
        unlink();
      }
    };

    return attempt(false);
  }
}
