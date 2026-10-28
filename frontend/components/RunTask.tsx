import { useState } from 'react';
import type { Row } from '../api';

export function RunTask({
  data,
  officeId,
  close,
  onSave,
  serverError = '',
}: {
  serverError?: string;
  data: Record<string, Row[]>;
  officeId: string;
  close: () => void;
  onSave: (value: Row) => Promise<void>;
}) {
  const [office, setOffice] = useState(officeId || data.offices?.[0]?.id || '');
  const [agent, setAgent] = useState('');
  const [request, setRequest] = useState('');
  const [procedure, setProcedure] = useState('');
  const [inputs, setInputs] = useState(
    JSON.stringify({ output_name: `reporte-${Date.now()}.xlsx` }, null, 2),
  );
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const agents =
    data.agents?.filter((a) => a.office_id === office && a.status !== 'disabled') || [];
  const selected =
    agent || data.offices?.find((o) => o.id === office)?.coordinator_id || agents[0]?.id || '';
  return (
    <div className="overlay">
      <form
        className="modal"
        onSubmit={async (e) => {
          e.preventDefault();
          setSaving(true);
          try {
            await onSave({
              office_id: office,
              agent_id: selected,
              request: request || 'Ejecutar procedimiento',
              procedure_id: procedure || null,
              inputs: procedure ? JSON.parse(inputs) : {},
            });
          } catch (e) {
            setError(String(e));
          } finally {
            setSaving(false);
          }
        }}
      >
        <div className="section-title">
          <h2>Nueva tarea</h2>
          <button type="button" onClick={close}>
            Cerrar
          </button>
        </div>
        <label>
          Oficina
          <select
            aria-label="Oficina"
            value={office}
            onChange={(e) => {
              setOffice(e.target.value);
              setAgent('');
              setProcedure('');
            }}
          >
            {data.offices?.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Agente responsable
          <select
            aria-label="Agente responsable"
            required
            value={selected}
            onChange={(e) => setAgent(e.target.value)}
          >
            <option value="">Seleccione agente</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Modo
          <select
            aria-label="Modo"
            value={procedure}
            onChange={(e) => setProcedure(e.target.value)}
          >
            <option value="">Solicitud IA en lenguaje natural</option>
            {data.procedures
              ?.filter((p) => p.office_id === office)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  Procedimiento: {p.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          Solicitud
          <textarea
            aria-label="Solicitud"
            required={!procedure}
            rows={4}
            value={request}
            onChange={(e) => setRequest(e.target.value)}
            placeholder="Analiza estos datos y genera un Excel en el recurso autorizado…"
          />
        </label>
        {procedure && (
          <label>
            Entradas del procedimiento (JSON)
            <textarea
              aria-label="Entradas del procedimiento (JSON)"
              rows={5}
              value={inputs}
              onChange={(e) => setInputs(e.target.value)}
            />
          </label>
        )}
        <p className="muted">
          La IA solo utiliza herramientas y recursos asignados. Se registra la ejecución completa.
          Las APIs externas siguen la política del agente.
        </p>
        {(error || serverError) && (
          <p role="alert" className="alert error">
            {error || serverError}
          </p>
        )}
        <button className="primary" disabled={saving || !selected}>
          {saving ? 'Creando…' : 'Ejecutar tarea'}
        </button>
      </form>
    </div>
  );
}
