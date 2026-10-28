import { useEffect, useState } from 'react';
import { api, BASE, getToken, type Row } from '../api';

export function Backups({ onAction }: { onAction: (action: () => Promise<any>) => Promise<any> }) {
  const [rows, setRows] = useState<Row[]>([]);
  const load = () => api('backups').then(setRows);
  useEffect(() => {
    void onAction(load);
  }, [onAction]);
  return (
    <section>
      <h2>Backups locales</h2>
      <p>
        Guarda una copia consistente de la base de datos dentro de data/backups. Las credenciales de
        Windows se conservan en su vault y requieren configuración separada al migrar de PC.
      </p>
      <button
        className="primary"
        onClick={() =>
          void onAction(async () => {
            await api('backups', 'POST');
            await load();
          })
        }
      >
        Crear backup
      </button>
      {rows.map((row) => (
        <div className="list-row" key={row.name}>
          <div>
            <strong>{row.name}</strong>
            <small>{Math.round(row.bytes / 1024)} KB</small>
          </div>
          <button
            onClick={() =>
              void onAction(async () => {
                const response = await fetch(BASE + '/api/backups/' + row.name + '/download', {
                  headers: { Authorization: 'Bearer ' + getToken() },
                });
                if (!response.ok) throw new Error('No se pudo descargar backup');
                const url = URL.createObjectURL(await response.blob());
                const link = document.createElement('a');
                link.href = url;
                link.download = row.name;
                link.click();
                setTimeout(() => URL.revokeObjectURL(url), 1000);
              })
            }
          >
            Descargar copia
          </button>
        </div>
      ))}
      <p className="muted">
        Restauración desde interfaz y programación automática: pendientes. SQLite: restaure con
        aplicación cerrada. PostgreSQL: pg_restore.
      </p>
    </section>
  );
}
