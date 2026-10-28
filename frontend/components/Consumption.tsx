import type { Row } from '../api';

export function Consumption({ value, data }: { value: Row; data: Record<string, Row[]> }) {
  return (
    <section>
      <h2>Consumo IA</h2>
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
