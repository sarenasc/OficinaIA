import { useRef, useState } from 'react';
import { api, type Row } from '../api';

const template = {
  version: 1,
  coordinator: 'coordinador',
  agents: [
    {
      key: 'coordinador',
      name: 'Coordinador',
      role: 'Coordinador de tareas',
      goal: 'Organizar las solicitudes y delegar a especialistas.',
      instructions:
        'Delega solo a agentes autorizados. Verifica los resultados y comunica los errores.',
      delegates: ['analista', 'reportes'],
      mode: 'safe',
      external_policy: 'never',
    },
    {
      key: 'analista',
      name: 'Analista',
      role: 'Analista de datos',
      goal: 'Analizar datos reales.',
      tools: ['filesystem.list', 'excel.read', 'excel.chart'],
      mode: 'safe',
    },
    {
      key: 'reportes',
      name: 'Generador de Reportes',
      role: 'Especialista en reportes',
      goal: 'Crear archivos y reportes comprobados.',
      tools: ['excel.create', 'excel.generate_sales'],
      mode: 'safe',
    },
  ],
};

export function AgentImport({
  offices,
  initialOffice,
  onClose,
  onImported,
}: {
  offices: Row[];
  initialOffice: string;
  onClose: () => void;
  onImported: () => Promise<void>;
}) {
  const [office, setOffice] = useState(initialOffice || offices[0]?.id || '');
  const [batch, setBatch] = useState<Row | null>(null);
  const [preview, setPreview] = useState<Row | null>(null);
  const [filename, setFilename] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const selection = useRef(0);

  const downloadTemplate = () => {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(template, null, 2)], { type: 'application/json' }),
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = 'plantilla-agentes.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const validate = async () => {
    const version = selection.current;
    setBusy(true);
    setError('');
    setPreview(null);
    try {
      const value = await api(`offices/${office}/agents/import?preview=true`, 'POST', batch);
      if (version === selection.current) setPreview(value);
    } catch (e) {
      if (version === selection.current) setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="overlay">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="agent-import-title"
      >
        <div className="section-title">
          <h2 id="agent-import-title">Importar agentes desde JSON</h2>
          <button disabled={busy} onClick={onClose}>
            Cerrar
          </button>
        </div>
        <p>
          Selecciona una oficina y un archivo con hasta 100 agentes. Se crean juntos; no se
          reemplazan agentes existentes.
        </p>
        <button onClick={downloadTemplate}>Descargar plantilla JSON</button>
        <label>
          Oficina de destino
          <select
            value={office}
            disabled={busy}
            onChange={(e) => {
              selection.current++;
              setOffice(e.target.value);
              setPreview(null);
              setError('');
            }}
          >
            {offices.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Archivo JSON
          <input
            type="file"
            accept=".json,application/json"
            disabled={busy}
            onChange={async (e) => {
              const current = ++selection.current;
              setBatch(null);
              setPreview(null);
              setError('');
              setFilename('');
              const file = e.target.files?.[0];
              if (!file) return;
              try {
                if (file.size > 2 * 1024 * 1024) throw new Error('El archivo supera 2 MB');
                const parsed = JSON.parse((await file.text()).replace(/^\uFEFF/, ''));
                if (current === selection.current) {
                  setBatch(parsed);
                  setFilename(file.name);
                }
              } catch (err) {
                if (current === selection.current) setError(String(err));
              }
            }}
          />
        </label>
        {filename && <p>{filename}</p>}
        {error && (
          <p className="alert error" role="alert">
            {error}
          </p>
        )}
        <button disabled={busy || !office || !batch} onClick={() => void validate()}>
          Validar y ver agentes
        </button>
        {preview && (
          <>
            <p>
              {preview.count} agentes. Coordinador: {preview.coordinator || 'Conservar el actual'}.
            </p>
            <div style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Agente</th>
                    <th>Modelo</th>
                    <th>Herramientas</th>
                    <th>Delega a</th>
                    <th>Modo / API</th>
                    <th>Capacidades</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.agents.map((a: Row) => (
                    <tr key={a.key}>
                      <td>{a.name}</td>
                      <td>{a.model || 'Predeterminado del proveedor'}</td>
                      <td>{a.tools.join(', ') || 'Sin herramientas'}</td>
                      <td>{a.delegates.join(', ') || 'Nadie'}</td>
                      <td>
                        {a.mode} / {a.external_policy}
                      </td>
                      <td>{a.permissions.join(', ') || 'Ninguna'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              Los recursos, conexiones y habilidades se asignan después en Herramientas y permisos.
              Configura proveedor y modelo si faltan.
            </p>
            <button
              className="primary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setError('');
                try {
                  await api(`offices/${office}/agents/import?preview=false`, 'POST', batch);
                  await onImported();
                  onClose();
                } catch (e) {
                  setError(String(e));
                  setPreview(null);
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? 'Importando…' : `Crear ${preview.count} agentes`}
            </button>
          </>
        )}
      </section>
    </div>
  );
}
