import type { Row } from '../api';

export function ExternalConnectionFields({
  kind,
  value,
  onChange,
}: {
  kind: string;
  value: Row;
  onChange: (value: Row) => void;
}) {
  const auth = ['bearer', 'header', 'none'].includes(value.auth) ? value.auth : 'bearer';
  const update = (key: string, next: unknown) =>
    onChange({ ...value, ...(kind === 'http_api' ? { auth } : {}), [key]: next });
  return (
    <fieldset>
      <legend>{kind === 'web_search' ? 'Búsqueda web' : 'API externa'}</legend>
      {kind === 'web_search' ? (
        <p>
          Proveedor disponible: Brave Search. Guarda la conexión y configura su clave con Configurar
          credencial.
        </p>
      ) : (
        <>
          <label>
            URL base de la API
            <input
              type="url"
              value={value.base_url || ''}
              placeholder="https://api.ejemplo.com/v1/"
              onChange={(event) => update('base_url', event.target.value)}
            />
          </label>
          <label>
            Autenticación API
            <select value={auth} onChange={(event) => update('auth', event.target.value)}>
              <option value="bearer">Bearer</option>
              <option value="header">Clave en cabecera</option>
              <option value="none">Sin credencial</option>
            </select>
          </label>
          {value.auth === 'header' && (
            <label>
              Cabecera de la clave
              <input
                value={value.auth_header || 'X-API-Key'}
                onChange={(event) => update('auth_header', event.target.value)}
              />
            </label>
          )}
          <label>
            <input
              type="checkbox"
              checked={!!value.allow_private}
              onChange={(event) => update('allow_private', event.target.checked)}
            />{' '}
            API privada explícita (cada tarea pedirá aprobación)
          </label>
        </>
      )}
      <label>
        Solicitudes por minuto
        <input
          type="number"
          min="1"
          max="60"
          value={value.requests_per_minute ?? 30}
          onChange={(event) => update('requests_per_minute', Number(event.target.value))}
        />
      </label>
      <small>
        La clave se guarda por separado en Windows Credential Manager. Los agentes necesitan la
        conexión asignada y la capacidad internet.access. No se prueba ni conecta al guardar.
      </small>
    </fieldset>
  );
}
