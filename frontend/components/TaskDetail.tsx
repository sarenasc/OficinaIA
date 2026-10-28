import { api, download, type Row } from '../api';
import { Status } from './Status';

export function TaskDetail({
  details,
  data,
  onAction,
  refresh,
}: {
  details: Row;
  data: Record<string, Row[]>;
  onAction: (action: () => Promise<any>) => Promise<any>;
  refresh: () => Promise<void>;
}) {
  const task = details.task;
  const pending = (details.approvals || []).filter((approval: Row) => approval.status === 'pending');
  return (
    <section>
      <div className="section-title">
        <h2>{task.number}</h2>
        <Status value={task.status} />
        {!['completed', 'error', 'cancelled'].includes(task.status) && (
          <button
            className="danger"
            onClick={() =>
              void onAction(async () => {
                await api(`tasks/${task.id}/cancel`, 'POST');
                await refresh();
              })
            }
          >
            Cancelar
          </button>
        )}
      </div>
      <p>{task.request}</p>
      {task.error && <div className="alert error">{task.error}</div>}
      {task.result && <pre>{task.result}</pre>}
      {task.status === 'waiting_approval' && pending.length === 0 && <p role="status">Esperando cargar la aprobación. Pulsa Actualizar si no aparece.</p>}
      {pending.map((a: Row) => (
          <div className="approval" key={a.id}>
            <h3>Se requiere aprobación</h3>
            <p>{a.reason}</p>
            <details>
              <summary>Ver acción exacta</summary>
              <pre>{JSON.stringify(a.payload, null, 2)}</pre>
            </details>
            <div className="actions">
              <button
                className="primary"
                onClick={() =>
                  void onAction(async () => {
                    await api(`approvals/${a.id}/decide`, 'POST', {
                      approved: true,
                    });
                    await refresh();
                  })
                }
              >
                Autorizar esta tarea
              </button>
              <button
                onClick={() =>
                  void onAction(async () => {
                    await api(`approvals/${a.id}/decide`, 'POST', {
                      approved: false,
                    });
                    await refresh();
                  })
                }
              >
                Rechazar
              </button>
            </div>
          </div>
        ))}
      <h3>Flujo de ejecución</h3>
      <div className="execution-flow">
        {details.executions?.map((e: Row, i: number) => (
          <details key={e.id} className="execution">
            <summary>
              <span className="step">{i + 1}</span>
              <strong>{data.agents?.find((a) => a.id === e.agent_id)?.name || e.agent_id}</strong>
              <small>
                {e.tool_name || `${e.provider} / ${e.model}`} · {e.duration_ms} ms
              </small>
              <Status value={e.status} />
            </summary>
            <h4>Recibió</h4>
            <pre>{JSON.stringify(e.input, null, 2)}</pre>
            <h4>Respondió</h4>
            <pre>{JSON.stringify(e.output, null, 2)}</pre>
            {e.error && <p role="alert">{e.error}</p>}
          </details>
        ))}
      </div>
      {details.artifacts?.map((a: Row) => (
        <div className="list-row" key={a.id}>
          <div>
            <strong>{a.name}</strong>
            <small>{a.path}</small>
          </div>
          <button onClick={() => void onAction(() => download(a.id, a.name))}>Descargar</button>
          <button onClick={() => void onAction(() => api(`artifacts/${a.id}/open`, 'POST'))}>
            Abrir archivo
          </button>
          <button onClick={() => void onAction(() => api(`artifacts/${a.id}/open-folder`, 'POST'))}>
            Abrir ubicación
          </button>
        </div>
      ))}
      <details>
        <summary>Conversación interna ({details.messages?.length || 0})</summary>
        {details.messages?.map((message: Row) => (
          <div key={message.id}>
            <p>
              {data.agents?.find((a) => a.id === message.source_id)?.name} →{' '}
              {data.agents?.find((a) => a.id === message.target_id)?.name}
            </p>
            <pre>{message.content}</pre>
          </div>
        ))}
      </details>
    </section>
  );
}
