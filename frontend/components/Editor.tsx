import { useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import type { Row } from '../api';
import { defaults, forms, labels, payload } from '../forms';
import { SQLConnectionFields } from './SQLConnectionFields';
import { ExternalConnectionFields } from './ExternalConnectionFields';

const officeIcons = [
  { value: 'building', symbol: '▦', label: 'Oficina' },
  { value: '🏆', symbol: '🏆', label: 'Deportes' },
  { value: '⚽', symbol: '⚽', label: 'Fútbol' },
  { value: '📊', symbol: '📊', label: 'Análisis' },
  { value: '💰', symbol: '💰', label: 'Finanzas' },
  { value: '💻', symbol: '💻', label: 'Tecnología' },
  { value: '📣', symbol: '📣', label: 'Marketing' },
  { value: '👥', symbol: '👥', label: 'Personas' },
  { value: '🛠️', symbol: '🛠️', label: 'Operaciones' },
  { value: '📚', symbol: '📚', label: 'Educación' },
  { value: '🔬', symbol: '🔬', label: 'Investigación' },
  { value: '🌱', symbol: '🌱', label: 'Agricultura' },
];

export function Editor({
  entity,
  row,
  data,
  officeId,
  close,
  onSave,
  serverError = '',
}: {
  serverError?: string;
  entity: string;
  row?: Row;
  data: Record<string, Row[]>;
  officeId: string;
  close: () => void;
  onSave: (value: any) => Promise<void>;
}) {
  const [draft, setDraft] = useState<Row>(() => {
    const value = { ...defaults(entity, officeId), ...row };
    for (const f of forms[entity] || [])
      if (f.type === 'json') value[f.key] = JSON.stringify(value[f.key], null, 2);
    return value;
  });
  const [error, setError] = useState('');
  const [secret, setSecret] = useState('');
  const [saving, setSaving] = useState(false);
  return (
    <div className="overlay">
      <form
        className="modal"
        onSubmit={async (event) => {
          event.preventDefault();
          setSaving(true);
          try {
            await onSave(entity === 'credential' ? secret : payload(entity, draft));
          } catch (e) {
            setError(String(e));
          } finally {
            setSaving(false);
          }
        }}
      >
        <div className="section-title">
          <h2>
            {entity === 'credential'
              ? 'Credencial segura'
              : (row ? 'Editar ' : 'Crear ') + labels[entity]}
          </h2>
          <button type="button" onClick={close}>
            Cerrar
          </button>
        </div>
        {(error || serverError) && (
          <p role="alert" className="alert error">
            {error || serverError}
          </p>
        )}
        {entity === 'credential' ? (
          <label>
            API key / contraseña
            <input
              type="password"
              autoComplete="new-password"
              required
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
            />
            <small>
              Se guarda en Windows Credential Manager. No se registra en logs ni base de datos.
            </small>
          </label>
        ) : (
          (forms[entity] || []).map((field) => {
            const update = (value: any) => setDraft((old) => ({ ...old, [field.key]: value }));
            if (
              entity === 'connections' &&
              ['http_api', 'web_search'].includes(draft.kind) &&
              field.key === 'config'
            ) {
              let config: Row = {};
              try {
                config = JSON.parse(draft.config || '{}');
              } catch {
                /* Config is edited by fields below. */
              }
              return (
                <ExternalConnectionFields
                  key={field.key}
                  kind={draft.kind}
                  value={config}
                  onChange={(value) => update(JSON.stringify(value, null, 2))}
                />
              );
            }
            if (field.type === 'icon') {
              const icons = officeIcons.some((icon) => icon.value === draft[field.key])
                ? officeIcons
                : [
                    ...officeIcons,
                    {
                      value: draft[field.key] || '',
                      symbol: draft[field.key] || '—',
                      label: 'Actual',
                    },
                  ];
              return (
                <fieldset key={field.key} className="icon-picker">
                  <legend>{field.label}</legend>
                  <div className="icon-options">
                    {icons.map((icon) => (
                      <label
                        key={icon.value}
                        className={`icon-option${draft[field.key] === icon.value ? ' is-selected' : ''}`}
                      >
                        <input
                          type="radio"
                          name={field.key}
                          value={icon.value}
                          checked={draft[field.key] === icon.value}
                          onChange={() => update(icon.value)}
                        />
                        <span className="icon-symbol" aria-hidden="true">
                          {icon.symbol}
                        </span>
                        <span>{icon.label}</span>
                      </label>
                    ))}
                  </div>
                  <small>Elige el icono que mejor represente tu oficina.</small>
                </fieldset>
              );
            }
            if (entity === 'connections' && draft.kind === 'sqlserver' && field.key === 'config') {
              let config: Row = {};
              try {
                config = JSON.parse(draft.config || '{}');
              } catch {
                /* Other database JSON remains editable when switching. */
              }
              return (
                <SQLConnectionFields
                  key={field.key}
                  value={config}
                  onChange={(value) => update(JSON.stringify(value, null, 2))}
                />
              );
            }
            const choices = field.entity
              ? (data[field.entity] || []).filter(
                  (item) =>
                    !item.office_id ||
                    item.office_id === draft.office_id ||
                    (entity === 'offices' && item.office_id === row?.id),
                )
              : [];
            return (
              <label key={field.key}>
                {field.label}
                {field.entity || field.options ? (
                  <select
                    aria-label={field.label}
                    required={field.required}
                    value={draft[field.key] ?? ''}
                    onChange={(e) => update(e.target.value || null)}
                  >
                    <option value="">Seleccionar…</option>
                    {field.entity
                      ? choices.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.name}
                          </option>
                        ))
                      : [
                          ...new Set([
                            ...(field.options || []),
                            ...(draft[field.key] ? [draft[field.key]] : []),
                          ]),
                        ].map((value) => (
                          <option key={value} value={value}>
                            {value}
                          </option>
                        ))}
                  </select>
                ) : field.type === 'json' || field.type === 'textarea' ? (
                  <textarea
                    rows={field.type === 'json' ? 5 : 3}
                    value={draft[field.key] || ''}
                    onChange={(e) => update(e.target.value)}
                  />
                ) : field.type === 'checkbox' ? (
                  <input
                    type="checkbox"
                    checked={!!draft[field.key]}
                    onChange={(e) => update(e.target.checked)}
                  />
                ) : (
                  <div className="input-row">
                    <input
                      required={field.required}
                      type={field.type === 'number' ? 'number' : 'text'}
                      step="any"
                      value={draft[field.key] ?? ''}
                      onChange={(e) => update(e.target.value)}
                    />
                    {field.type === 'path' && '__TAURI_INTERNALS__' in window && (
                      <button
                        type="button"
                        onClick={async () => {
                          const selected = await open({
                            directory: draft.kind !== 'file',
                            multiple: false,
                          });
                          if (typeof selected === 'string') update(selected);
                        }}
                      >
                        Seleccionar
                      </button>
                    )}
                  </div>
                )}
                {field.help && <small>{field.help}</small>}
              </label>
            );
          })
        )}
        <div className="actions">
          <button type="button" onClick={close}>
            Cancelar
          </button>
          <button className="primary" disabled={saving}>
            {saving ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </form>
    </div>
  );
}
