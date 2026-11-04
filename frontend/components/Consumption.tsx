import { useState } from 'react';
import { BASE, getToken, type Row } from '../api';

function isoDate(date: Date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

export function ActivityReport() {
  const today = new Date();
  const [from, setFrom] = useState(isoDate(new Date(today.getTime() - 30 * 86400000)));
  const [to, setTo] = useState(isoDate(today));
  const [state, setState] = useState('');
  async function download() {
    setState('Generando…');
    try {
      const response = await fetch(`${BASE}/api/reports/activity.xlsx?desde=${from}&hasta=${to}`, {
        headers: { Authorization: 'Bearer ' + getToken() },
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || 'No se pudo generar el informe');
      }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');
      link.href = url;
      link.download = `actividad_agentes_${from}_${to}.xlsx`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setState('');
    } catch (e) {
      setState(String(e instanceof Error ? e.message : e));
    }
  }
  return (
    <div className="report-download">
      <h3>Informe de actividad en Excel</h3>
      <p className="muted">
        Agentes trabajando y sin actividad, tareas realizadas, tokens y USD estimado por fecha.
      </p>
      <label>
        Desde <input type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} />
      </label>{' '}
      <label>
        Hasta <input type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)} />
      </label>{' '}
      <button
        className="primary"
        disabled={!from || !to || from > to}
        onClick={() => void download()}
      >
        Descargar Excel
      </button>
      {state && <p role="status">{state}</p>}
    </div>
  );
}

export function Consumption({ value, data }: { value: Row; data: Record<string, Row[]> }) {
  return (
    <section>
      <h2>Consumo IA</h2>
      <ActivityReport />
      <p className="muted">
        USD estimado según tarifas configuradas. Sin tarifa, el costo permanece desconocido. Fechas
        en America/Santiago.
      </p>
      <div className="metrics">
        {[
          ['Total', value.total],
          ['Hoy', value.day],
          ['Mes', value.month],
        ].map(([label, bucket]) => (
          <div key={String(label)}>
            <span>{String(label)}</span>
            <strong>${Number(bucket?.estimated_usd || 0).toFixed(4)}</strong>
            <small>
              {bucket?.external_calls || 0} llamadas externas · {bucket?.local_calls || 0} LOCAL ·{' '}
              {bucket?.unpriced_calls || 0} sin precio
            </small>
          </div>
        ))}
      </div>
      {(['by_agent', 'by_office', 'by_task'] as const).map((key) => (
        <details key={key}>
          <summary>
            {
              {
                by_agent: 'Por agente',
                by_office: 'Por oficina',
                by_task: 'Por tarea',
              }[key]
            }
          </summary>
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Entrada</th>
                <th>Salida</th>
                <th>USD conocido</th>
                <th>Sin precio</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(value[key] || {}).map(([id, raw]) => {
                const bucket = raw as Row;
                const entity = data[
                  {
                    by_agent: 'agents',
                    by_office: 'offices',
                    by_task: 'tasks',
                  }[key]
                ]?.find((row) => row.id === id);
                return (
                  <tr key={id}>
                    <td>{entity?.name || entity?.number || id}</td>
                    <td>{bucket.tokens_in}</td>
                    <td>{bucket.tokens_out}</td>
                    <td>{Number(bucket.estimated_usd).toFixed(4)}</td>
                    <td>{bucket.unpriced_calls}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </details>
      ))}
    </section>
  );
}
