import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../data/site');

export function load<T = any>(name: string): T {
  return JSON.parse(readFileSync(path.join(DATA, `${name}.json`), 'utf8')) as T;
}

export const meta = load('meta');
export const leagues: any[] = load('leagues');
export const people: Record<string, any> = load('people');
export const standings: Record<string, any[]> = load('standings');
export const weekly: Record<string, Record<string, any>> = load('weekly');
export const highs = load('highs');
export const records = load('records');
export const power: any[] = load('power');

export const leagueByCode: Record<string, any> = Object.fromEntries(leagues.map((l) => [l.code, l]));

/** Prefix a site-relative path with the deploy base (GitHub Pages project path). */
export function u(p: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  return `${base}/${p.replace(/^\//, '')}`;
}

export const personUrl = (slotId: string | null) => (slotId ? u(`people/${slotId.toLowerCase()}/`) : '#');
export const leagueUrl = (code: string) => u(`leagues/${code.toLowerCase()}/`);

export const fmt = (n: number | null | undefined, d = 2) =>
  n === null || n === undefined ? '–' : n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

export const signed = (n: number) => (n > 0 ? `+${fmt(n)}` : fmt(n));

export function fmtDateET(iso: string | undefined): string {
  if (!iso) return 'never';
  return new Date(iso).toLocaleString('en-US', {
    timeZone: 'America/New_York', weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  }) + ' ET';
}

export function isStale(iso: string | undefined, days = 8): boolean {
  if (!iso) return true;
  return Date.now() - new Date(iso).getTime() > days * 86400e3;
}

export const record = (r: any) => (r ? `${r.wins}-${r.losses}${r.ties ? `-${r.ties}` : ''}` : '–');
