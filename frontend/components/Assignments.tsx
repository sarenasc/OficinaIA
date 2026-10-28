import { useEffect, useState } from 'react';
import { api, type Row } from '../api';

export function Assignments({
  agent,
  data,
  close,
  onSave,
  serverError = '',
}: {
  serverError?: string;
  agent: Row;
  data: Record<string, Row[]>;
  close: () => void;
  onSave: (value: Row) => Promise<any>;
}) {
  const [value, setValue] = useState<Row | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    void api(`agents/${agent.id}/assignments`)
      .then(setValue)
      .catch((e) => setError(String(e)));
  }, [agent.id]);
  const simple = (key: string, id: string) =>
    setValue(
      (old) =>
        old && {
          ...old,
          [key]: old[key].includes(id)
            ? old[key].filter((x: string) => x !== id)
            : [...old[key], id],
        },
    );
  const permission = (key: string, idKey: string, id: string, p: string) =>
    setValue((old) => {
      if (!old) return old;
      const existing = old[key].find((r: Row) => r[idKey] === id) || {
        [idKey]: id,
        permissions: [],
      };
      const updated = {
        ...existing,
        permissions: existing.permissions.includes(p)
          ? existing.permissions.filter((x: string) => x !== p)
          : [...existing.permissions, p],
      };
      return {
        ...old,
        [key]: [
          ...old[key].filter((r: Row) => r[idKey] !== id),
          ...(updated.permissions.length ? [updated] : []),
        ],
      };
    });
  return (
    <div className="overlay">
      <form
        className="modal"
        onSubmit={async (e) => {
          e.preventDefault();
          if (value) await onSave(value);
        }}
      >
        <div className="section-title">
          <h2>Capacidades de {agent.name}</h2>
          <button type="button" onClick={close}>
            Cerrar
          </button>
        </div>
        {(error || serverError) && (
          <p role="alert" className="alert error">
            {error || serverError}
          </p>
        )}
        {value && (
          <>
            <h3>Herramientas</h3>
            {data.tools?.map((row) => (
              <label className="check" key={row.id}>
                <input
                  type="checkbox"
                  checked={value.tools.includes(row.id)}
                  onChange={() => simple('tools', row.id)}
                />
                {row.name}
              </label>
            ))}
            <h3>Habilidades</h3>
            {data.skills?.map((row) => (
              <label className="check" key={row.id}>
                <input
                  type="checkbox"
                  checked={value.skills.includes(row.id)}
                  onChange={() => simple('skills', row.id)}
                />
                {row.name}
              </label>
            ))}
            <h3>Recursos · autorización explícita</h3>
            {data.resources?.map((row) => (
              <div key={row.id} className="permission">
                <strong>{row.name}</strong>
                <small>{row.path}</small>
                <div className="actions">
                  {['read', 'create', 'modify', 'delete'].map((p) => (
                    <label className="check" key={p}>
                      <input
                        type="checkbox"
                        checked={
                          value.resources
                            .find((r: Row) => r.resource_id === row.id)
                            ?.permissions.includes(p) || false
                        }
                        onChange={() => permission('resources', 'resource_id', row.id, p)}
                      />
                      {p}
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <h3>Conexiones · lectura y escritura autorizada</h3>
            {data.connections?.map((row) => (
              <div key={row.id} className="permission">
                <strong>{row.name}</strong>
                <div className="actions">
                  {['connect', 'select', 'execute'].map((p) => (
                    <label className="check" key={p}>
                      <input
                        type="checkbox"
                        checked={
                          value.connections
                            .find((r: Row) => r.connection_id === row.id)
                            ?.permissions.includes(p) || false
                        }
                        onChange={() => permission('connections', 'connection_id', row.id, p)}
                      />
                      {p}
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <p className="muted">
              Python requiere además la capacidad python.execute en la configuración del agente.
              Trusted conserva estas restricciones.
            </p>
            <button className="primary">Guardar asignaciones</button>
          </>
        )}
      </form>
    </div>
  );
}
