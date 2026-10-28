import { useCallback, useEffect, useState } from 'react';
import { api, BASE, getToken, initialize, download, type Row } from './api';
import { forms, labels } from './forms';
import { Status } from './components/Status';
import { EntityList } from './components/EntityList';
import { Editor } from './components/Editor';
import { Assignments } from './components/Assignments';
import { OfficeScene } from './components/OfficeScene';
import { OfficeGraph } from './components/OfficeGraph';
import { RunTask } from './components/RunTask';
import { TaskList } from './components/TaskList';
import { TaskDetail } from './components/TaskDetail';
import { DemoForm } from './components/DemoForm';
import { Consumption } from './components/Consumption';
import { Backups } from './components/Backups';
import { AgentImport } from './components/AgentImport';
import { SkillImport } from './components/SkillImport';
import { ExecutionSettings } from './components/ExecutionSettings';

export function App() {
  const [ready, setReady] = useState(false);
  const [section, setSection] = useState('offices');
  const [officeId, setOfficeId] = useState('');
  const [data, setData] = useState<Record<string, Row[]>>({});
  const [dashboard, setDashboard] = useState<Row>({});
  const [health, setHealth] = useState<Row>({});
  const [consumption, setConsumption] = useState<Row>({});
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editor, setEditor] = useState<{ entity: string; row?: Row } | null>(null);
  const [assignmentAgent, setAssignmentAgent] = useState<Row | null>(null);
  const [taskId, setTaskId] = useState('');
  const [taskDetails, setTaskDetails] = useState<Row | null>(null);
  const [runOpen, setRunOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [importAgents, setImportAgents] = useState(false);
  const [importSkills, setImportSkills] = useState(false);

  const perform = useCallback(async (action: () => Promise<any>) => {
    setError('');
    setBusy(true);
    try {
      return await action();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);
  const refresh = useCallback(async () => {
    const modules = [
      'offices',
      'agents',
      'areas',
      'tools',
      'resources',
      'connections',
      'providers',
      'skills',
      'procedures',
      'relations',
      'tasks',
      'artifacts',
      'audit',
    ];
    const values = await Promise.all(modules.map((module) => api(module)));
    setData(Object.fromEntries(modules.map((key, i) => [key, values[i]])));
    const [d, h, c] = await Promise.all([api('dashboard'), api('health'), api('consumption')]);
    setDashboard(d);
    setHealth(h);
    setConsumption(c);
  }, []);
  useEffect(() => {
    let stopped = false;
    async function connect() {
      await initialize();
      for (let attempt = 0; attempt < 30 && !stopped; attempt++) {
        try {
          await refresh();
          setReady(true);
          setError('');
          return;
        } catch (e) {
          if (attempt === 29)
            setError(
              'Backend no disponible. Revise el lanzador, servicios y puerto 38080. ' + String(e),
            );
        }
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }
    void connect();
    return () => {
      stopped = true;
    };
  }, [refresh]);
  useEffect(() => {
    if (!ready) return;
    const timer = setInterval(() => {
      void refresh().catch((e) => setError(String(e)));
    }, 5000);
    return () => clearInterval(timer);
  }, [ready, refresh]);
  useEffect(() => {
    if (!taskId || !ready) return;
    let stopped = false;
    setTaskDetails(null);
    const load = () =>
      api(`tasks/${taskId}/details`)
        .then((value) => {
          if (!stopped) setTaskDetails(value);
        })
        .catch((e) => setError(String(e)));
    void load();
    const socket = new WebSocket(BASE.replace('http:', 'ws:') + '/ws/tasks/' + taskId);
    socket.onopen = () => socket.send(JSON.stringify({ token: getToken() }));
    socket.onmessage = (event) => {
      if (!stopped) setTaskDetails(JSON.parse(event.data));
    };
    const timer = setInterval(() => {
      void load();
    }, 3000);
    return () => {
      stopped = true;
      clearInterval(timer);
      socket.close();
    };
  }, [taskId, ready]);

  const waitingTasks = (data.tasks || []).filter(
    (task) => task.status === 'waiting_approval' && (!officeId || task.office_id === officeId),
  );
  const currentOffice = data.offices?.find((o) => o.id === officeId);
  const rows = (data[section] || []).filter(
    (row) => !officeId || !row.office_id || row.office_id === officeId,
  );
  async function remove(entity: string, row: Row) {
    if (
      !confirm(
        `¿Eliminar ${row.name || row.id}? Si existe historial relacionado, deberá desactivarlo.`,
      )
    )
      return;
    await perform(async () => {
      await api(`${entity}/${row.id}`, 'DELETE');
      await refresh();
    });
  }
  async function test(entity: string, row: Row) {
    await perform(async () => {
      const result = await api(`${entity}/${row.id}/test`, 'POST');
      setNotice(
        result.models
          ? 'Modelos disponibles: ' + (result.models.join(', ') || 'ninguno instalado')
          : result.notice || 'Conexión comprobada',
      );
    });
  }
  async function credential(entity: string, row: Row) {
    setEditor({ entity: 'credential', row: { ...row, entity } });
  }
  return (
    <div className="app">
      <aside>
        <div className="brand">
          <span className="logo">O</span>
          <div>
            Oficina IA<small>LOCAL · WINDOWS</small>
          </div>
        </div>
        <nav>
          {Object.entries(labels).map(([key, label]) => (
            <button
              key={key}
              className={section === key ? 'selected' : ''}
              onClick={() => {
                setSection(key);
                setTaskId('');
              }}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="local">
          <span className={ready ? 'dot' : 'dot offline'} />
          {ready ? 'Backend conectado' : 'Conectando backend…'}
          <small>Persistencia: {health.database || '—'}</small>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <p className="eyebrow">TU PLATAFORMA DE AGENTES</p>
            <h1>{labels[section]}</h1>
            <p className="muted">
              {currentOffice ? currentOffice.name : 'Todas las oficinas'} · configuración
              persistente en este PC
            </p>
          </div>
          <div className="header-actions">
            <select
              aria-label="Filtrar oficina"
              value={officeId}
              onChange={(e) => setOfficeId(e.target.value)}
            >
              <option value="">Todas las oficinas</option>
              {data.offices?.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
            <button onClick={() => void perform(refresh)}>Actualizar</button>
            <button
              className="primary"
              disabled={!ready || busy || !data.agents?.length}
              onClick={() => setRunOpen(true)}
            >
              Nueva tarea
            </button>
          </div>
        </header>
        {error && (
          <div role="alert" className="alert error">
            {error}
            <button onClick={() => setError('')}>Cerrar</button>
          </div>
        )}
        {notice && (
          <div className="alert notice">
            {notice}
            <button onClick={() => setNotice('')}>Cerrar</button>
          </div>
        )}
        {busy && <p role="status">Procesando…</p>}
        {waitingTasks.length > 0 && (
          <section className="alert notice" aria-label="Aprobaciones pendientes">
            <strong>{waitingTasks.length} tarea(s) esperando tu aprobación</strong>
            {waitingTasks.map((task) => (
              <p key={task.id}>
                {task.number} ·{' '}
                {data.agents?.find((agent) => agent.id === task.agent_id)?.name || 'Agente'}{' '}
                <button
                  onClick={() => {
                    setSection('tasks');
                    setTaskId(task.id);
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                >
                  Revisar aprobación
                </button>
              </p>
            ))}
          </section>
        )}
        {!ready && (
          <section className="empty">
            <h2>Iniciando servicios locales</h2>
            <p>
              La interfaz requiere el backend iniciado con un token de sesión. En desarrollo utilice{' '}
              <code>npm run dev:local</code>.
            </p>
          </section>
        )}
        {ready && section === 'dashboard' && (
          <>
            <div className="metrics">
              {[
                ['Oficinas', dashboard.offices],
                ['Agentes', dashboard.agents],
                ['Tareas', dashboard.tasks],
                ['Archivos', dashboard.artifacts],
              ].map(([label, count]) => (
                <section key={label}>
                  <span>{label}</span>
                  <strong>{count || 0}</strong>
                </section>
              ))}
            </div>
            <section>
              <h2>Actividad y consumo</h2>
              <div className="metrics">
                <div>
                  <strong>{dashboard.task_states?.executing || 0}</strong>
                  Ejecutando
                </div>
                <div>
                  <strong>{dashboard.task_states?.completed || 0}</strong>
                  Completadas
                </div>
                <div>
                  <strong>{dashboard.task_states?.error || 0}</strong>Errores
                </div>
                <div>
                  <strong>{dashboard.consumption?.local_calls || 0}</strong>
                  Llamadas LOCAL
                </div>
              </div>
              <p>
                APIs externas: {dashboard.consumption?.external_calls || 0} llamadas · entrada:{' '}
                {dashboard.consumption?.tokens_in || 0} tokens · salida:{' '}
                {dashboard.consumption?.tokens_out || 0} tokens.
              </p>
              <p>
                Costo conocido estimado: USD{' '}
                {Number(dashboard.consumption?.estimated_usd || 0).toFixed(4)}. Llamadas sin precio:{' '}
                {dashboard.consumption?.unpriced_calls || 0}.
              </p>
            </section>
            <Consumption value={consumption} data={data} />
            <TaskList
              rows={(data.tasks || []).slice(0, 8)}
              onOpen={(id) => {
                setTaskId(id);
                setSection('tasks');
              }}
            />
          </>
        )}
        {ready && section === 'offices' && (
          <>
            <div className="section-title">
              <h2>{officeId ? 'Oficina seleccionada' : 'Mis oficinas'}</h2>
              <button className="primary" onClick={() => setEditor({ entity: 'offices' })}>
                + Nueva oficina
              </button>
            </div>
            <div className="cards">
              {(officeId ? data.offices?.filter((o) => o.id === officeId) : data.offices)?.map(
                (o) => (
                  <section className="office-card" key={o.id}>
                    <div className="office-icon">{o.icon === 'building' ? '▦' : o.icon}</div>
                    <h2>{o.name}</h2>
                    <p>{o.description || 'Define su estructura, agentes y objetivos.'}</p>
                    <p className="muted">
                      {data.agents?.filter((a) => a.office_id === o.id).length} agentes ·{' '}
                      {o.active ? 'Activa' : 'Desactivada'}
                      {o.demo ? ' · DEMO' : ''}
                    </p>
                    <div className="actions">
                      <button
                        className="primary"
                        onClick={() => {
                          setOfficeId(o.id);
                          setSection('agents');
                        }}
                      >
                        Abrir oficina
                      </button>
                      <button onClick={() => setEditor({ entity: 'offices', row: o })}>
                        Editar
                      </button>
                      <button
                        onClick={() =>
                          void perform(async () => {
                            await api(`offices/${o.id}/duplicate`, 'POST');
                            await refresh();
                          })
                        }
                      >
                        Duplicar
                      </button>
                      <button className="danger" onClick={() => void remove('offices', o)}>
                        Eliminar
                      </button>
                    </div>
                  </section>
                ),
              )}
            </div>
            {!data.offices?.length && (
              <section className="empty">
                <h2>Construye tu primera oficina</h2>
                <p>
                  Define libremente su nombre, estructura y agentes. La aplicación no impone
                  departamentos ni roles.
                </p>
                <button className="primary" onClick={() => setEditor({ entity: 'offices' })}>
                  Crear oficina
                </button>
              </section>
            )}
          </>
        )}
        {ready && section === 'agents' && (
          <>
            <div className="section-title">
              <h2>{officeId ? 'Oficina y agentes' : 'Agentes'}</h2>
              <button disabled={!data.offices?.length} onClick={() => setImportAgents(true)}>
                Importar JSON
              </button>
              <button
                className="primary"
                disabled={!data.offices?.length}
                onClick={() => setEditor({ entity: 'agents' })}
              >
                + Crear agente
              </button>
            </div>
            {officeId && (
              <OfficeScene
                key={officeId}
                officeId={officeId}
                onConfigure={() => setSection('providers')}
                onTask={(id) => {
                  setTaskId(id);
                  setSection('tasks');
                }}
              />
            )}
            {officeId && <h3>Organigrama</h3>}
            {officeId && (
              <OfficeGraph
                key={`${officeId}:${rows.map((row) => row.id).join(',')}`}
                agents={rows}
                relations={data.relations || []}
                onEdit={(row) => setEditor({ entity: 'agents', row })}
                onAction={perform}
                refresh={refresh}
              />
            )}
            <EntityList
              entity="agents"
              providerModels={Object.fromEntries(
                (data.providers || []).map((provider) => [provider.id, provider.default_model]),
              )}
              rows={rows}
              onEdit={(row) => setEditor({ entity: 'agents', row })}
              onRemove={(row) => void remove('agents', row)}
              extras={(row) => (
                <button onClick={() => setAssignmentAgent(row)}>Herramientas y permisos</button>
              )}
            />
          </>
        )}
        {ready && forms[section] && !['offices', 'agents'].includes(section) && (
          <>
            <div className="section-title">
              <h2>Elementos configurados</h2>
              {section === 'skills' && (
                <button onClick={() => setImportSkills(true)}>Importar JSON</button>
              )}
              <button className="primary" onClick={() => setEditor({ entity: section })}>
                + Crear
              </button>
            </div>
            {section === 'connections' && (
              <p className="muted">
                Guarda una configuración por servidor y base de datos. Puedes dejarlas inactivas y
                completarlas después; cada agente recibe sus conexiones por separado.
              </p>
            )}
            {section === 'tools' && (
              <p className="muted">
                Integradas: archivos, Excel, SQL, internet/APIs, PDF y Python Docker.
                Personalizadas: SQL de lectura y Python. PowerShell y programas Windows: pendientes.
              </p>
            )}
            <EntityList
              entity={section}
              rows={rows}
              onEdit={(row) => setEditor({ entity: section, row })}
              onRemove={(row) => void remove(section, row)}
              extras={(row) =>
                ['providers', 'connections'].includes(section) ? (
                  <>
                    <button
                      disabled={section === 'connections' && !row.active}
                      onClick={() => void test(section, row)}
                    >
                      Probar conexión
                      {section === 'providers' ? ' / modelos' : ''}
                    </button>
                    <button onClick={() => void credential(section, row)}>
                      {row.has_credential ? 'Actualizar credencial' : 'Configurar credencial'}
                    </button>
                  </>
                ) : section === 'procedures' ? (
                  <button
                    onClick={() => {
                      setOfficeId(row.office_id);
                      setRunOpen(true);
                    }}
                  >
                    Ejecutar procedimiento
                  </button>
                ) : null
              }
            />
          </>
        )}
        {ready && section === 'tasks' && (
          <>
            {taskId && (!taskDetails || taskDetails.task.id !== taskId) && (
              <p role="status">Cargando detalle de tarea…</p>
            )}
            {taskDetails && taskDetails.task.id === taskId && (
              <TaskDetail details={taskDetails} data={data} onAction={perform} refresh={refresh} />
            )}
            <TaskList
              rows={rows}
              onOpen={(id) => {
                setTaskId(id);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
            />
          </>
        )}
        {ready && section === 'audit' && (
          <section>
            <h2>Eventos registrados</h2>
            {rows.map((row) => (
              <details key={row.id}>
                <summary>
                  {new Date(row.created_at).toLocaleString('es-CL')} · {row.action}
                </summary>
                <pre>{JSON.stringify(row.details, null, 2)}</pre>
              </details>
            ))}
          </section>
        )}
        {ready && section === 'artifacts' && (
          <section>
            <h2>Archivos generados</h2>
            {rows.map((row) => (
              <div className="list-row" key={row.id}>
                <div>
                  <strong>{row.name}</strong>
                  <small>{row.path}</small>
                  <small>
                    Agente: {data.agents?.find((a) => a.id === row.agent_id)?.name} · tarea:{' '}
                    {data.tasks?.find((t) => t.id === row.task_id)?.number}
                  </small>
                </div>
                <button onClick={() => void perform(() => download(row.id, row.name))}>
                  Descargar / guardar copia
                </button>
              </div>
            ))}
            {!rows.length && <p>Aún no hay archivos generados.</p>}
          </section>
        )}
        {ready && section === 'settings' && (
          <>
            <ExecutionSettings />
            <section>
              <h2>Servicios locales</h2>
              <p>
                Base de datos: {health.database}. Docker:{' '}
                {health.docker_installed ? 'detectado' : 'no detectado'}. Ollama:{' '}
                {health.ollama_installed ? 'detectado' : 'no detectado en PATH'}.
              </p>
              <p>
                Las conexiones reales se prueban en Proveedores IA y Conexiones. Python arbitrario
                necesita Docker Desktop iniciado y la imagen del sandbox construida.
              </p>
              <p className="muted">
                Inicio automático Docker desde interfaz, programas Windows arbitrarios y empaquetado
                instalable: pendientes.
              </p>
              <button
                onClick={() =>
                  void perform(async () => {
                    const diagnostics = await api('services/diagnostics', 'POST');
                    setNotice(JSON.stringify(diagnostics));
                  })
                }
              >
                Diagnosticar servicios
              </button>
            </section>
            <Backups onAction={perform} />
            <section>
              <h2>Demo opcional</h2>
              <p>
                Instala una oficina separada, tres agentes y un procedimiento que genera un Excel
                real desde CSV. Autoriza explícitamente una carpeta de salida.
              </p>
              <DemoForm
                onAction={perform}
                refresh={refresh}
                onInstalled={(id) => {
                  setOfficeId(id);
                  setSection('procedures');
                }}
              />
              <button
                className="danger"
                onClick={() => {
                  if (
                    confirm(
                      '¿Eliminar configuración e historial demo? Los Excel de su carpeta se conservarán.',
                    )
                  )
                    void perform(async () => {
                      await api('demo/remove', 'DELETE');
                      setOfficeId('');
                      await refresh();
                    });
                }}
              >
                Eliminar demo
              </button>
            </section>
          </>
        )}
      </main>
      {importSkills && (
        <SkillImport
          onClose={() => setImportSkills(false)}
          onImported={async () => {
            setNotice(
              'Habilidades importadas. Asígnalas a los agentes en Herramientas y permisos.',
            );
            await refresh();
          }}
        />
      )}
      {importAgents && (
        <AgentImport
          offices={data.offices || []}
          initialOffice={officeId}
          onClose={() => setImportAgents(false)}
          onImported={async () => {
            setNotice(
              'Agentes importados. Configura sus proveedores y permisos antes de ejecutar tareas.',
            );
            await refresh();
          }}
        />
      )}
      {editor && (
        <Editor
          entity={editor.entity}
          row={editor.row}
          data={data}
          serverError={error}
          officeId={officeId}
          close={() => setEditor(null)}
          onSave={async (value) => {
            const saved = await perform(async () => {
              if (editor.entity === 'credential')
                await api(`${editor.row!.entity}/${editor.row!.id}/credential`, 'POST', { value });
              else
                await api(
                  `${editor.entity}${editor.row ? '/' + editor.row.id : ''}`,
                  editor.row ? 'PATCH' : 'POST',
                  value,
                );
              await refresh();
              return true;
            });
            if (saved) setEditor(null);
          }}
        />
      )}
      {assignmentAgent && (
        <Assignments
          agent={assignmentAgent}
          data={data}
          serverError={error}
          close={() => setAssignmentAgent(null)}
          onSave={(value) =>
            perform(async () => {
              await api(`agents/${assignmentAgent.id}/assignments`, 'PUT', value);
              setAssignmentAgent(null);
              await refresh();
            })
          }
        />
      )}
      {runOpen && (
        <RunTask
          data={data}
          serverError={error}
          officeId={officeId}
          close={() => setRunOpen(false)}
          onSave={async (value) => {
            const task = await perform(async () => {
              const result = await api('tasks', 'POST', value);
              await refresh();
              return result;
            });
            if (task) {
              setRunOpen(false);
              setTaskId(task.id);
              setSection('tasks');
            }
          }}
        />
      )}
    </div>
  );
}
