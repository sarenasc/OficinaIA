import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';

type Engine = { available: boolean; error: string | null; tools: string[]; python?: string; packages?: Record<string, string> };
type Job = { id: string; operation: string; fixed_operation?: string; backend: string; status: string; duration_ms?: number; error?: string };
type State = { mode: string; docker: Engine; native: Engine; active_jobs: number; last_error: string | null; jobs: Job[] };

export function ExecutionSettings() {
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    setBusy(true); setError('');
    try { setState(await api('execution/diagnostics', 'POST')); }
    catch (cause) { setError(String(cause)); }
    finally { setBusy(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  async function select(mode: string) {
    setBusy(true); setError('');
    try {
      await api('execution/preference', 'PUT', { mode });
      await refresh();
    } catch (cause) { setError(String(cause)); }
    finally { setBusy(false); }
  }
  return <section>
    <h2>Motor de ejecución</h2>
    {error && <p role="alert">{error}</p>}
    <label>Modo seleccionado
      <select value={state?.mode || 'auto'} disabled={busy || !state} onChange={event => void select(event.target.value)}>
        <option value="auto">Automático</option><option value="docker">Docker</option><option value="native">Windows nativo</option>
      </select>
    </label>
    <p>python.execute admite cálculos y CSV con operation/parameters en Windows. Para código Python generado por agentes se requiere Docker.</p>
    {state && <>
      <p>Docker: {state.docker.available ? 'disponible' : state.docker.error}. Herramientas: {state.docker.tools.join(', ')}.</p>
      <p>Trabajador Windows: {state.native.available ? 'disponible' : state.native.error}. Python: {state.native.python || 'sin detectar'}.</p>
      <p>Paquetes: {state.native.packages ? Object.entries(state.native.packages).map(([name, version]) => `${name} ${version}`).join(', ') : 'sin detectar'}. Herramientas: {state.native.tools.join(', ')}.</p>
      <p>Trabajos activos: {state.active_jobs}. Último error: {state.last_error || 'ninguno'}.</p>
      {state.jobs.length > 0 && <table><thead><tr><th>Operación</th><th>Motor</th><th>Tiempo</th><th>Estado</th></tr></thead><tbody>
        {state.jobs.map(job => <tr key={job.id}><td>{job.fixed_operation || job.operation}</td><td>{job.backend}</td><td>{job.duration_ms === undefined ? 'En curso / sin dato' : `${job.duration_ms} ms`}</td><td>{job.status}{job.error && `: ${job.error}`}</td></tr>)}
      </tbody></table>}
    </>}
    <button disabled={busy} onClick={() => void refresh()}>{busy ? 'Diagnosticando…' : 'Probar diagnóstico / actualizar'}</button>
  </section>;
}
