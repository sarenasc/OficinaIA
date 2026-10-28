import { lazy, Suspense, useRef, useState, type PointerEvent } from 'react';
import { api, type Row } from '../api';
import { Status } from './Status';
import { AgentActivity } from './AgentActivity';
import './office2d.css';

import { useOfficeStream } from './useOfficeStream';
import { OfficeWalker } from './OfficeWalker';
import { clampPosition, defaultPosition, type Point } from './officePaths';
import { useOllamaStatus } from './useOllamaStatus';
import { FloorplanEditor, FloorplanLayer } from './FloorplanEditor';
import { EMPTY_STRUCTURE, structureHeight, wallsOf, type Structure } from './floorplan';
const Office3D = lazy(() => import('./Office3D'));
export function OfficeScene({
  officeId,
  onTask,
  onConfigure,
}: {
  officeId: string;
  onTask: (id: string) => void;
  onConfigure: () => void;
}) {
  const { scene, setScene, connection } = useOfficeStream(officeId);
  const ollama = useOllamaStatus();
  const connected = connection !== 'offline';
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<{ id: string; offset: Point } | null>(null);
  const [selected, setSelected] = useState('');
  const [view, setView] = useState<'2d' | '3d'>('3d');
  const [editing, setEditing] = useState(false);
  const [editRevision, setEditRevision] = useState(0);
  const [desks, setDesks] = useState<Record<string, Point>>({});
  const [structure, setStructure] = useState<Structure>(EMPTY_STRUCTURE);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const agents: Row[] = scene?.agents || [];
  function position(agent: Row, index: number): Point {
    return (editing ? desks[agent.id] : scene?.layout?.desks?.[agent.id]) || defaultPosition(index);
  }
  const building: Structure = editing
    ? structure
    : { rooms: scene?.layout?.rooms || [], partitions: scene?.layout?.partitions || [] };
  const walls = wallsOf(building);
  const height = Math.max(
    structureHeight(building),
    ...agents.map((a, i) => position(a, i).y + 500),
  );
  const obstacles = agents.map(position);
  function pointer(e: PointerEvent<SVGGElement>): Point | null {
    const matrix = svg.current?.getScreenCTM();
    if (!matrix) return null;
    const point = new DOMPoint(e.clientX, e.clientY).matrixTransform(matrix.inverse());
    return { x: point.x, y: point.y };
  }
  const person = agents.find((a) => a.id === selected);
  async function save() {
    setSaving(true);
    setError('');
    try {
      const layout = await api(`offices/${officeId}/layout`, 'PUT', {
        revision: editRevision,
        desks,
        ...structure,
      });
      setScene((current) => (current ? { ...current, layout } : current));
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }
  if (!scene)
    return <p role="status">{connected ? 'Cargando oficina…' : 'Conectando con la oficina…'}</p>;
  return (
    <section
      className={`office-scene ${connected ? '' : 'disconnected'}`}
      aria-label={view === '3d' ? 'Oficina 3D' : 'Oficina 2D'}
    >
      <div className="scene-toolbar">
        <div>
          <strong>
            {scene.office.name} · Oficina {view === '3d' ? '3D' : '2D'}
          </strong>
          <p className="ollama-state">
            {!ollama
              ? 'Comprobando Ollama…'
              : !ollama.reachable
                ? 'Ollama sin conexión'
                : `Ollama conectado · ${agents.filter((agent) => ollama.providers.some((provider: Row) => provider.ready_agents.includes(agent.id))).length} agentes con modelo listo`}
            <button onClick={onConfigure}>Configurar IA</button>
          </p>
          <p className="muted">
            {connected
              ? connection === 'live'
                ? 'En vivo · WebSocket conectado'
                : 'Recuperando conexión · respaldo REST'
              : 'Sin conexión · animaciones pausadas'}{' '}
            · {agents.length} personas
          </p>
        </div>
        <div className="office-view-switch">
          <button aria-pressed={view === '3d'} disabled={editing} onClick={() => setView('3d')}>
            Oficina 3D
          </button>
          <button aria-pressed={view === '2d'} onClick={() => setView('2d')}>
            Plano 2D
          </button>
        </div>
        {editing ? (
          <div>
            <button
              disabled={saving}
              onClick={() => {
                setEditing(false);
                setError('');
              }}
            >
              Cancelar
            </button>
            <button disabled={saving || !connected} onClick={() => void save()}>
              Guardar distribución
            </button>
          </div>
        ) : (
          <button
            disabled={!connected}
            onClick={() => {
              setView('2d');
              setDesks(Object.fromEntries(agents.map((a, i) => [a.id, position(a, i)])));
              setEditRevision(scene.layout.revision || 0);
              setStructure({
                rooms: scene.layout.rooms || [],
                partitions: scene.layout.partitions || [],
              });
              setEditing(true);
            }}
          >
            Construir oficina
          </button>
        )}
      </div>
      {editing && (
        <p className="scene-instructions">
          Añade salas y divisiones. Arrastra las salas, paredes y escritorios o usa las flechas al
          seleccionarlos. Guarda para conservar el diseño.
        </p>
      )}
      <p className="scene-instructions">
        {view === '2d'
          ? 'Las visitas entre escritorios representan delegaciones registradas; cada persona vuelve a su puesto.'
          : 'Estados reales del motor. Los paseos a cafetería y descanso son ambientación y no ejecutan tareas.'}
      </p>
      {error && <p role="alert">{error}</p>}
      {editing && <FloorplanEditor value={structure} onChange={setStructure} disabled={saving} />}
      <div className="scene-body">
        {view === '3d' ? (
          <Suspense fallback={<p>Cargando oficina 3D…</p>}>
            <Office3D
              agents={agents}
              positions={obstacles}
              structure={building}
              connected={connected}
              onSelect={setSelected}
              onFallback={() => setView('2d')}
            />
          </Suspense>
        ) : (
          <div className="scene-canvas">
            <svg
              ref={svg}
              viewBox={`0 0 1200 ${height}`}
              role="group"
              aria-label="Sala y escritorios de agentes"
            >
              <defs>
                <pattern id="office-floor" width="60" height="60" patternUnits="userSpaceOnUse">
                  <rect width="60" height="60" fill="#edf0e7" />
                  <path d="M0 60V0H60" stroke="#dde2d6" fill="none" />
                </pattern>
              </defs>
              <rect
                x="20"
                y="20"
                width="1160"
                height={height - 40}
                rx="24"
                fill="url(#office-floor)"
                stroke="#aab9b5"
                strokeWidth="8"
              />
              <path d="M80 55H370 M490 55H780 M900 55H1110" stroke="#8ecbd2" strokeWidth="18" />
              <text x="65" y="110" fill="#486760" fontSize="23" fontWeight="600">
                OFICINA · EQUIPO EN VIVO
              </text>
              {[80, 1120].map((x) => (
                <g key={x} transform={`translate(${x},${height - 85})`}>
                  <rect x="-20" y="-8" width="40" height="30" rx="8" fill="#b57c57" />
                  <circle cy="-20" r="30" fill="#639b71" />
                  <circle cx="-15" cy="-30" r="15" fill="#84b384" />
                </g>
              ))}
              <FloorplanLayer
                value={building}
                onChange={setStructure}
                disabled={saving}
                editing={editing}
              />
              {agents.map((agent, i) => {
                const p = position(agent, i);
                const state =
                  agent.activity?.task_status === 'waiting_approval' && agent.status === 'waiting'
                    ? 'approval'
                    : agent.status;
                const color = ['#557dd1', '#be7595', '#5b9c81', '#ad874e'][i % 4];
                return (
                  <g
                    key={agent.id}
                    transform={`translate(${p.x},${p.y})`}
                    className={`desk ${state}`}
                    role="button"
                    tabIndex={0}
                    aria-label={`${agent.name}: ${state}`}
                    onClick={() => setSelected(agent.id)}
                    onPointerDown={(e) => {
                      if (!editing || saving) return;
                      const point = pointer(e);
                      if (!point) return;
                      setSelected(agent.id);
                      drag.current = {
                        id: agent.id,
                        offset: { x: point.x - p.x, y: point.y - p.y },
                      };
                      e.currentTarget.setPointerCapture(e.pointerId);
                    }}
                    onPointerMove={(e) => {
                      const active = drag.current;
                      if (!active || active.id !== agent.id) return;
                      const point = pointer(e);
                      if (!point) return;
                      setDesks((current) => ({
                        ...current,
                        [agent.id]: clampPosition({
                          x: point.x - active.offset.x,
                          y: point.y - active.offset.y,
                        }),
                      }));
                    }}
                    onPointerUp={() => {
                      drag.current = null;
                    }}
                    onPointerCancel={() => {
                      drag.current = null;
                    }}
                    onLostPointerCapture={() => {
                      drag.current = null;
                    }}
                    onKeyDown={(e) => {
                      const arrows: Record<string, Point> = {
                        ArrowLeft: { x: -10, y: 0 },
                        ArrowRight: { x: 10, y: 0 },
                        ArrowUp: { x: 0, y: -10 },
                        ArrowDown: { x: 0, y: 10 },
                      };
                      if (editing && !saving && arrows[e.key]) {
                        e.preventDefault();
                        setDesks((current) => ({
                          ...current,
                          [agent.id]: clampPosition({
                            x: p.x + arrows[e.key].x,
                            y: p.y + arrows[e.key].y,
                          }),
                        }));
                        return;
                      }
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setSelected(agent.id);
                      }
                    }}
                  >
                    {selected === agent.id && (
                      <rect
                        x="-103"
                        y="-75"
                        width="206"
                        height="205"
                        rx="18"
                        fill="none"
                        stroke="#3264b3"
                        strokeWidth="3"
                        strokeDasharray="7 5"
                      />
                    )}
                    <ellipse cy="30" rx="96" ry="60" fill="#172c2820" />
                    <rect
                      x="-91"
                      y="-65"
                      width="182"
                      height="91"
                      rx="12"
                      fill="#c89f75"
                      stroke="#ad8763"
                      strokeWidth="3"
                    />
                    <rect x="-45" y="-57" width="90" height="48" rx="5" fill="#344858" />
                    <rect
                      x="-38"
                      y="-51"
                      width="76"
                      height="34"
                      rx="2"
                      fill={state === 'working' ? '#9cd5e8' : '#bac9d0'}
                    />
                    <path d="M-28 -40H15 M-28 -32H28" stroke="#edfaff" strokeWidth="3" />
                    <rect x="-30" y="-3" width="60" height="13" rx="3" fill="#ece9df" />
                    <circle cx="64" cy="-26" r="11" fill="#f9f5eb" />
                    <circle cx="64" cy="-26" r="7" fill="#895a37" />
                    <rect x="-36" y="30" width="72" height="62" rx="24" fill="#52646a" />
                    <OfficeWalker
                      key={`${agent.id}:${scene.layout.revision}:${editing}`}
                      home={p}
                      height={height}
                      obstacles={obstacles}
                      walls={walls}
                      paused={!connected || editing}
                      eventId={
                        scene.messages?.find((message: Row) => message.source_id === agent.id)?.id
                      }
                      destination={(() => {
                        const message = scene.messages?.find(
                          (item: Row) => item.source_id === agent.id,
                        );
                        const index = agents.findIndex((item) => item.id === message?.target_id);
                        return index < 0 ? undefined : position(agents[index], index);
                      })()}
                    >
                      <g className="person">
                        <path
                          d="M-17 69L-22 94 M17 69L22 94"
                          stroke="#34465d"
                          strokeWidth="13"
                          strokeLinecap="round"
                        />
                        <rect
                          x="-27"
                          y="22"
                          width="54"
                          height="53"
                          rx="19"
                          fill={state === 'disabled' ? '#959b9d' : color}
                        />
                        <path
                          className="hands"
                          d="M-23 37L-35 12 M23 37L35 12"
                          stroke="#e1ac86"
                          strokeWidth="11"
                          strokeLinecap="round"
                        />
                        <circle cy="13" r="23" fill="#e8ba97" />
                        <path d="M-23 11Q-25 -18 0 -14Q25 -14 23 11L13 0H-13Z" fill="#554435" />
                        <circle cx="-7" cy="15" r="2" fill="#554435" />
                        <circle cx="7" cy="15" r="2" fill="#554435" />
                      </g>
                    </OfficeWalker>
                    <rect x="-98" y="109" width="196" height="46" rx="9" fill="white" />
                    <text textAnchor="middle" y="127" fontSize="14" fontWeight="600" fill="#253b4a">
                      {agent.name.length > 23 ? agent.name.slice(0, 21) + '…' : agent.name}
                    </text>
                    <text textAnchor="middle" y="145" fontSize="12" fill="#637681">
                      {{
                        working: 'Trabajando',
                        waiting: 'Esperando',
                        approval: 'Requiere aprobación',
                        error: 'Error',
                        disabled: 'Deshabilitado',
                        active: 'Disponible',
                      }[state as string] || state}
                    </text>
                  </g>
                );
              })}
              {!agents.length && (
                <text x="600" y="300" textAnchor="middle" fill="#637681">
                  Crea agentes para ocupar los escritorios
                </text>
              )}
            </svg>
          </div>
        )}
        {editing && person && (
          <aside className="scene-panel">
            {person ? (
              <>
                <h3>{person.name}</h3>
                <p>{person.role || 'Agente'}</p>
                <Status value={person.status} />
                <AgentActivity agent={person} onTask={onTask} />
                {editing && (
                  <fieldset>
                    <legend>Posición del escritorio</legend>
                    {(['x', 'y'] as const).map((axis) => (
                      <label key={axis}>
                        {axis.toUpperCase()}
                        <input
                          type="number"
                          min={axis === 'x' ? 100 : 130}
                          max={axis === 'x' ? 1100 : 3800}
                          step="10"
                          value={desks[person.id]?.[axis] || 0}
                          onChange={(e) => {
                            const value = Number(e.target.value);
                            setDesks((current) => ({
                              ...current,
                              [person.id]: {
                                ...current[person.id],
                                [axis]: Math.max(
                                  axis === 'x' ? 100 : 130,
                                  Math.min(axis === 'x' ? 1100 : 3800, value),
                                ),
                              },
                            }));
                          }}
                        />
                      </label>
                    ))}
                  </fieldset>
                )}
              </>
            ) : (
              <>
                <h3>Tu equipo</h3>
                <p>Selecciona una persona para ver su actividad y abrir la tarea.</p>
                <p className="muted">
                  El organigrama y las herramientas siguen disponibles debajo.
                </p>
              </>
            )}
          </aside>
        )}
      </div>
      <section className="team-activity" aria-label="Actividad del equipo">
        <h3>Actividad del equipo</h3>
        {!connected && (
          <p className="muted">Sin conexión: estos datos pueden estar desactualizados.</p>
        )}
        <div className="team-activity-grid">
          {agents.map((agent) => (
            <article
              key={agent.id}
              className={`agent-activity-card ${agent.activity?.error ? 'has-error' : ''} ${selected === agent.id ? 'is-selected' : ''}`}
            >
              <button
                className="activity-agent-name"
                aria-pressed={selected === agent.id}
                onClick={() => setSelected(agent.id)}
              >
                {agent.name}
              </button>
              <Status value={agent.status} />
              <AgentActivity agent={agent} onTask={onTask} />
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
