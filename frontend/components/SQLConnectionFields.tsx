import type { Row } from '../api';

export function SQLConnectionFields({
  value,
  onChange,
}: {
  value: Row;
  onChange: (value: Row) => void;
}) {
  function update(key: string, next: unknown) {
    const config = { ...value };
    if (next === undefined || next === '') delete config[key];
    else config[key] = next;
    onChange(config);
  }
  return (
    <fieldset>
      <legend>Configuración de SQL Server</legend>
      <p className="muted">
        Puedes guardar esta configuración incompleta con Activo desmarcado y completarla después.
        Crea una conexión por servidor y base de datos.
      </p>
      <label>
        Servidor o servidor\instancia
        <input
          aria-label="Servidor o instancia SQL"
          placeholder="SERVIDOR\INSTANCIA o dirección IP"
          value={value.host || ''}
          onChange={(event) => update('host', event.target.value)}
        />
      </label>
      <label>
        Base de datos
        <input
          aria-label="Base de datos SQL"
          value={value.database || ''}
          onChange={(event) => update('database', event.target.value)}
        />
      </label>
      <label>
        Autenticación
        <select
          aria-label="Autenticación SQL"
          value={value.auth || 'windows'}
          onChange={(event) => update('auth', event.target.value)}
        >
          <option value="windows">Windows</option>
          <option value="password">Usuario SQL y contraseña</option>
        </select>
      </label>
      {value.auth === 'password' && (
        <label>
          Usuario SQL
          <input
            aria-label="Usuario SQL"
            autoComplete="off"
            value={value.username || ''}
            onChange={(event) => update('username', event.target.value)}
          />
        </label>
      )}
      <label>
        Puerto opcional
        <input
          aria-label="Puerto SQL"
          type="number"
          min="1"
          max="65535"
          value={value.port ?? ''}
          onChange={(event) =>
            update('port', event.target.value ? Number(event.target.value) : undefined)
          }
        />
      </label>
      <label>
        Driver ODBC
        <input
          aria-label="Driver ODBC"
          value={value.driver ?? 'ODBC Driver 18 for SQL Server'}
          onChange={(event) => update('driver', event.target.value)}
        />
      </label>
      <label>
        <input
          type="checkbox"
          checked={!!value.trust_certificate}
          onChange={(event) => update('trust_certificate', event.target.checked)}
        />{' '}
        Confiar en el certificado del servidor
      </label>
      <small>
        Windows utiliza la identidad que ejecuta Oficina IA. La contraseña SQL se configura con el
        botón Configurar credencial después de guardar. Guardar no intenta conectarse.
      </small>
      <label>
        <input
          type="checkbox"
          checked={!!value.writable_enabled}
          onChange={(event) => update('writable_enabled', event.target.checked)}
        />{' '}
        Habilitar escritura SQL con aprobación por tarea
      </label>
      {value.writable_enabled && (
        <>
          <label>
            Tablas autorizadas para escritura (separadas por coma)
            <input
              value={(value.write_tables || []).join(', ')}
              onChange={(event) =>
                update(
                  'write_tables',
                  event.target.value
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean),
                )
              }
              placeholder="dbo.partidos, dbo.estadisticas"
            />
          </label>
          <label>
            Máximo de filas modificadas
            <input
              type="number"
              min="1"
              max="10000"
              value={value.max_write_rows ?? 1000}
              onChange={(event) => update('max_write_rows', Number(event.target.value))}
            />
          </label>
          <small>
            El agente necesita sql.execute, capacidad sql.write y permisos connect/execute en esta
            conexión. Toda escritura requiere aprobación; DDL está prohibido.
          </small>
        </>
      )}
    </fieldset>
  );
}
