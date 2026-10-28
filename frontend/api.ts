import { invoke } from '@tauri-apps/api/core';

export type Row = Record<string, any>;
export const BASE = 'http://127.0.0.1:38080';
let token = '';
export async function initialize() {
  token =
    '__TAURI_INTERNALS__' in window
      ? await invoke<string>('session_token')
      : new URLSearchParams(window.location.hash.slice(1)).get('session') ||
        (import.meta as any).env.VITE_OFFICE_TOKEN || '';
  if (window.location.hash.startsWith('#session=')) {
    sessionStorage.setItem('office-session', token);
    history.replaceState(null, '', window.location.pathname + window.location.search);
  } else if (!token && !('__TAURI_INTERNALS__' in window)) {
    token = sessionStorage.getItem('office-session') || '';
  }
}
export function getToken() {
  return token;
}
export async function api(path: string, method = 'GET', data?: unknown): Promise<any> {
  const response = await fetch(BASE + '/api/' + path, {
    method,
    headers: {
      Authorization: 'Bearer ' + token,
      'Content-Type': 'application/json',
    },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  const value = await response.json();
  if (!response.ok)
    throw new Error(typeof value.detail === 'string' ? value.detail : JSON.stringify(value.detail));
  return value;
}
export async function download(id: string, name: string) {
  const response = await fetch(BASE + '/api/artifacts/' + id + '/download', {
    headers: { Authorization: 'Bearer ' + token },
  });
  if (!response.ok) throw new Error('No se pudo descargar el archivo; revise permiso de lectura');
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
