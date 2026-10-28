import { useRef, useState } from 'react';
import { api, type Row } from '../api';

const template = {
  version: 1,
  skills: [
    {
      name: 'Analizar ventas y crear gráfico Excel',
      description: 'Leer un libro de ventas y graficar totales por categoría.',
      instructions:
        'Identifica el archivo real con filesystem.list. Lee sus cabeceras con excel.read. Usa excel.chart para sumar la columna de ventas por categoría y agregar el gráfico. No calcules totales usando solo la muestra enviada al modelo. Comunica errores y espera las aprobaciones requeridas.',
      required_tools: ['filesystem.list', 'excel.read', 'excel.chart'],
      examples: 'Lee ventas.xlsx y suma total por producto en una pestaña nueva GraficoVentas.',
      output_format:
        'Ruta comprobada del archivo, hoja del gráfico, filas procesadas y total calculado.',
    },
  ],
};

export function SkillImport({
  onClose,
  onImported,
}: {
  onClose: () => void;
  onImported: () => Promise<void>;
}) {
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
    link.download = 'plantilla-habilidades.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return (
    <div className="overlay">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="skill-import-title"
      >
        <div className="section-title">
          <h2 id="skill-import-title">Importar habilidades desde JSON</h2>
          <button disabled={busy} onClick={onClose}>
            Cerrar
          </button>
        </div>
        <p>
          Crea hasta 100 habilidades juntas. Son compartidas entre oficinas y se asignan a los
          agentes después. No se reemplazan habilidades existentes.
        </p>
        <button onClick={downloadTemplate}>Descargar plantilla JSON</button>
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
              setFilename('');
              setError('');
              const file = e.target.files?.[0];
              if (!file) return;
              try {
                if (file.size > 2 * 1024 * 1024) throw new Error('El archivo supera 2 MB');
                const value = JSON.parse((await file.text()).replace(/^\uFEFF/, ''));
                if (current === selection.current) {
                  setBatch(value);
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
        <button
          disabled={busy || !batch}
          onClick={async () => {
            const current = selection.current;
            setBusy(true);
            setPreview(null);
            setError('');
            try {
              const value = await api('skills/import?preview=true', 'POST', batch);
              if (current === selection.current) setPreview(value);
            } catch (err) {
              if (current === selection.current) setError(String(err));
            } finally {
              setBusy(false);
            }
          }}
        >
          Validar y ver habilidades
        </button>
        {preview && (
          <>
            <p>Habilidades listas para crear: {preview.count}.</p>
            {preview.skills.map((skill: Row) => (
              <details key={skill.name}>
                <summary>
                  <strong>{skill.name}</strong>
                </summary>
                <p>{skill.description}</p>
                <p style={{ whiteSpace: 'pre-wrap' }}>{skill.instructions}</p>
                <p>Herramientas requeridas: {skill.required_tools.join(', ') || 'Ninguna'}</p>
                <p>Ejemplos: {skill.examples || 'Sin ejemplos'}</p>
                <p>Formato esperado: {skill.output_format || 'Sin formato definido'}</p>
              </details>
            ))}
            <p>
              Importar no ejecuta código ni habilita herramientas. Asigna la habilidad y sus
              herramientas en Agentes → Herramientas y permisos.
            </p>
            <button
              className="primary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setError('');
                try {
                  await api('skills/import?preview=false', 'POST', batch);
                  await onImported();
                  onClose();
                } catch (err) {
                  setError(String(err));
                  setPreview(null);
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? 'Importando…' : `Crear habilidades (${preview.count})`}
            </button>
          </>
        )}
      </section>
    </div>
  );
}
