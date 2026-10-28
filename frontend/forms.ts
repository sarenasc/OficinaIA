export type Field = {
  key: string;
  label: string;
  type?: string;
  options?: string[];
  entity?: string;
  required?: boolean;
  default?: any;
  help?: string;
};
const name: Field = { key: 'name', label: 'Nombre', required: true };
const description: Field = {
  key: 'description',
  label: 'Descripción',
  type: 'textarea',
  default: '',
};
const active: Field = {
  key: 'active',
  label: 'Activo',
  type: 'checkbox',
  default: true,
};
const office: Field = {
  key: 'office_id',
  label: 'Oficina',
  entity: 'offices',
  required: true,
};
export const forms: Record<string, Field[]> = {
  offices: [
    name,
    description,
    { key: 'icon', label: 'Icono', type: 'icon', default: 'building' },
    active,
    {
      key: 'coordinator_id',
      label: 'Coordinador opcional',
      entity: 'agents',
      default: null,
    },
  ],
  areas: [name, office, description],
  agents: [
    name,
    office,
    { key: 'area_id', label: 'Área opcional', entity: 'areas', default: null },
    description,
    { key: 'role', label: 'Rol libre', default: '' },
    { key: 'goal', label: 'Objetivo', type: 'textarea', default: '' },
    {
      key: 'instructions',
      label: 'Instrucciones del sistema',
      type: 'textarea',
      default: '',
    },
    {
      key: 'provider_id',
      label: 'Proveedor IA',
      entity: 'providers',
      default: null,
    },
    {
      key: 'model',
      label: 'Modelo (nombre instalado o identificador API)',
      default: '',
    },
    { key: 'temperature', label: 'Temperatura', type: 'number', default: 0.2 },
    {
      key: 'context_limit',
      label: 'Contexto máximo',
      type: 'number',
      default: 8192,
    },
    {
      key: 'mode',
      label: 'Modo de ejecución',
      options: ['safe', 'trusted'],
      default: 'safe',
    },
    {
      key: 'external_policy',
      label: 'Política API externa',
      options: ['never', 'ask', 'auto'],
      default: 'never',
    },
    {
      key: 'fallbacks',
      label: 'Fallbacks (JSON)',
      type: 'json',
      default: [],
      help: '[{"provider_id":"UUID", "model":"modelo"}]',
    },
    {
      key: 'permissions',
      label: 'Capacidades (JSON)',
      type: 'json',
      default: [],
        help: '["python.execute"] para scripts Docker; ["sports.analyze"] para análisis deportivo predefinido Windows/Docker',
    },
    { key: 'rules', label: 'Reglas', type: 'textarea', default: '' },
    {
      key: 'memory_mode',
      label: 'Memoria',
      options: ['off', 'session', 'persistent'],
      default: 'off',
    },
    {
      key: 'status',
      label: 'Estado',
      options: ['active', 'disabled', 'error'],
      default: 'active',
    },
  ],
  providers: [
    name,
    {
      key: 'kind',
      label: 'Tipo',
      options: ['ollama', 'openai', 'anthropic', 'gemini'],
      default: 'ollama',
    },
    {
      key: 'url',
      label: 'URL',
      default: 'http://127.0.0.1:11434',
      required: true,
    },
    { key: 'default_model', label: 'Modelo predeterminado', default: '' },
    active,
    {
      key: 'pricing',
      label: 'Precios USD por millón de tokens (JSON)',
      type: 'json',
      default: {},
      help: '{"modelo":{"input":1,"output":2}}. Sin precio, costo desconocido.',
    },
  ],
  resources: [
    name,
    {
      key: 'kind',
      label: 'Tipo',
      options: ['directory', 'network_directory', 'file', 'application', 'server', 'url', 'custom'],
      default: 'directory',
    },
    {
      key: 'path',
      label: 'Ruta absoluta o dirección',
      required: true,
      type: 'path',
    },
    description,
    active,
  ],
  connections: [
    name,
    {
      key: 'kind',
      label: 'Motor',
      options: ['sqlserver', 'postgresql', 'mysql', 'sqlite', 'http_api', 'web_search'],
      default: 'sqlserver',
    },
    {
      key: 'config',
      label: 'Configuración sin contraseña (JSON)',
      type: 'json',
      default: { host: '', database: '', auth: 'windows', driver: 'ODBC Driver 18 for SQL Server' },
      help: 'SQL: host, database, username, port, auth (windows/password), driver. SQLite: path absoluto. Configure contraseña por separado.',
    },
    { ...active, default: false },
  ],
  tools: [
    name,
    description,
    {
      key: 'kind',
      label: 'Ejecución',
      options: ['custom.sql', 'custom.python'],
      default: 'custom.sql',
    },
    {
      key: 'parameters',
      label: 'JSON Schema de parámetros',
      type: 'json',
      default: { type: 'object', properties: {}, additionalProperties: false },
    },
    {
      key: 'config',
      label: 'Configuración (JSON)',
      type: 'json',
      default: {},
      help: 'SQL: connection_id y query. Python: code y resources (UUIDs).',
    },
    {
      key: 'required_permissions',
      label: 'Permisos necesarios (JSON)',
      type: 'json',
      default: [],
    },
    {
      key: 'timeout',
      label: 'Timeout (segundos)',
      type: 'number',
      default: 60,
    },
    active,
  ],
  skills: [
    name,
    description,
    {
      key: 'instructions',
      label: 'Procedimiento / conocimiento',
      type: 'textarea',
      default: '',
    },
    {
      key: 'required_tools',
      label: 'IDs de herramientas requeridas (JSON)',
      type: 'json',
      default: [],
    },
    { key: 'examples', label: 'Ejemplos', type: 'textarea', default: '' },
    {
      key: 'output_format',
      label: 'Formato esperado',
      type: 'textarea',
      default: '',
    },
  ],
  procedures: [
    name,
    office,
    description,
    {
      key: 'steps',
      label: 'Pasos (JSON)',
      type: 'json',
      default: [],
      help: '[{"agent_id":"UUID", "tool":"csv.read", "arguments":{"resource_id":"UUID", "path":"$input.csv"}}]. Referencias: $input.nombre, $steps.0.rows.',
    },
  ],
};
export const labels: Record<string, string> = {
  dashboard: 'Resumen',
  offices: 'Oficinas',
  agents: 'Agentes',
  areas: 'Áreas',
  tools: 'Herramientas',
  skills: 'Habilidades',
  resources: 'Recursos',
  connections: 'Conexiones',
  providers: 'Proveedores IA',
  procedures: 'Procedimientos',
  tasks: 'Tareas',
  audit: 'Auditoría',
  artifacts: 'Archivos',
  settings: 'Configuración',
};
export function defaults(entity: string, officeId: string) {
  return Object.fromEntries(
    (forms[entity] || []).map((f) => [
      f.key,
      f.key === 'office_id' ? officeId : (f.default ?? (f.entity ? null : '')),
    ]),
  );
}
export function payload(entity: string, draft: Record<string, any>) {
  return Object.fromEntries(
    forms[entity].map((f) => [
      f.key,
      f.type === 'json'
        ? JSON.parse(draft[f.key] || 'null')
        : f.type === 'number'
          ? Number(draft[f.key])
          : draft[f.key] === '' && f.entity
            ? null
            : draft[f.key],
    ]),
  );
}
