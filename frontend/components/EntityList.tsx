import type { Row } from '../api';
import { Status } from './Status';

export function EntityList({
  entity,
  rows,
  onEdit,
  onRemove,
  extras,
  providerModels = {},
}: {
  entity: string;
  rows: Row[];
  onEdit: (r: Row) => void;
  onRemove: (r: Row) => void;
  extras?: (r: Row) => React.ReactNode;
  providerModels?: Record<string, string>;
}) {
  return (
    <section>
      {rows.map((row) => (
        <div className="list-row" key={row.id}>
          <div>
            <strong>{row.name}</strong>
            <p>{row.description || row.goal || row.kind}</p>
            <small className="id">ID: {row.id}</small>
            {entity === 'tools' && row.config?.risk && <small>Riesgo: {row.config.risk}</small>}
            {row.status && <Status value={row.status} />}
            {entity === 'connections' && (
              <p className="muted">
                {row.active ? 'Activa' : 'Guardada para configurar después'}
                {row.config?.host && ` · ${row.config.host}`}
                {row.config?.database && ` · ${row.config.database}`}
              </p>
            )}
            {entity === 'agents' && (
              <small>
                {row.model ||
                  (providerModels[row.provider_id]
                    ? `${providerModels[row.provider_id]} (proveedor)`
                    : 'Modelo sin configurar')}{' '}
                · {row.mode} · API: {row.external_policy}
              </small>
            )}
          </div>
          <div className="actions">
            {extras?.(row)}
            <button onClick={() => onEdit(row)}>Editar</button>
            <button className="danger" disabled={row.builtin} onClick={() => onRemove(row)}>
              Eliminar
            </button>
          </div>
        </div>
      ))}
      {!rows.length && (
        <div className="empty">No hay elementos. Crea el primero desde el botón superior.</div>
      )}
    </section>
  );
}
