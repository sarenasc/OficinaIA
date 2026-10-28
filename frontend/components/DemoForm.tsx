import { useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { api } from '../api';

export function DemoForm({
  onAction,
  refresh,
  onInstalled,
}: {
  onAction: (action: () => Promise<any>) => Promise<any>;
  refresh: () => Promise<void>;
  onInstalled: (id: string) => void;
}) {
  const [path, setPath] = useState('');
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void onAction(async () => {
          const demo = await api('demo/install', 'POST', { output_path: path });
          await refresh();
          onInstalled(demo.office.id);
        });
      }}
    >
      <label>
        Carpeta autorizada de salida
        <div className="input-row">
          <input
            required
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="C:\Reportes"
          />
          {'__TAURI_INTERNALS__' in window && (
            <button
              type="button"
              onClick={async () => {
                const result = await open({ directory: true, multiple: false });
                if (typeof result === 'string') setPath(result);
              }}
            >
              Seleccionar carpeta
            </button>
          )}
        </div>
      </label>
      <button className="primary">Instalar demo y autorizar creación de Excel</button>
    </form>
  );
}
