import { useRef, useState, type PointerEvent, type KeyboardEvent } from 'react';
import { snap, wallsOf, type Room, type Partition, type Structure } from './floorplan';

type Props = { value: Structure; onChange: (value: Structure) => void; disabled: boolean };

function MeasureInput({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (n: number) => void;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  return (
    <label>
      {label}
      <input
        type="number"
        min={min}
        max={max}
        step={20}
        value={draft ?? String(value)}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => {
          const number = draft === null || draft === '' ? value : Number(draft);
          if (Number.isFinite(number)) onChange(Math.max(min, Math.min(max, snap(number))));
          setDraft(null);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') e.currentTarget.blur();
        }}
      />
    </label>
  );
}

export function FloorplanEditor({ value, onChange, disabled }: Props) {
  const updateRoom = (id: string, patch: Partial<Room>) =>
    onChange({ ...value, rooms: value.rooms.map((r) => (r.id === id ? { ...r, ...patch } : r)) });
  const updatePartition = (id: string, patch: Partial<Partition>) =>
    onChange({
      ...value,
      partitions: value.partitions.map((p) => (p.id === id ? { ...p, ...patch } : p)),
    });
  function number(
    label: string,
    value: number,
    min: number,
    max: number,
    change: (n: number) => void,
  ) {
    return <MeasureInput label={label} value={value} min={min} max={max} onChange={change} />;
  }
  return (
    <fieldset className="floorplan-editor" disabled={disabled}>
      <legend>Constructor de oficina</legend>
      <p>
        Añade salas y divisiones, arrástralas en el plano y ajusta sus medidas. Las puertas dejan un
        paso de 100 unidades. Las medidas son unidades del plano.
      </p>
      <div className="floorplan-actions">
        <button
          disabled={value.rooms.length >= 40}
          onClick={() =>
            onChange({
              ...value,
              rooms: [
                ...value.rooms,
                {
                  id: crypto.randomUUID(),
                  name: `Sala ${value.rooms.length + 1}`,
                  x: 80,
                  y: Math.min(3600, Math.max(140, ...value.rooms.map((r) => r.y + r.depth + 40))),
                  width: 320,
                  depth: 300,
                  door: 'bottom',
                },
              ],
            })
          }
        >
          + Sala
        </button>
        <button
          disabled={value.partitions.length >= 80}
          onClick={() =>
            onChange({
              ...value,
              partitions: [
                ...value.partitions,
                {
                  id: crypto.randomUUID(),
                  x: 440,
                  y: 140,
                  length: 300,
                  orientation: 'vertical',
                  doorway: true,
                },
              ],
            })
          }
        >
          + División
        </button>
      </div>
      <div className="floorplan-cards">
        {value.rooms.map((r) => (
          <fieldset key={r.id}>
            <legend>{r.name || 'Sala'}</legend>
            <label>
              Nombre
              <input
                maxLength={60}
                value={r.name}
                onChange={(e) => updateRoom(r.id, { name: e.target.value })}
              />
            </label>
            <div className="floorplan-fields">
              {number('X', r.x, 60, 1140 - r.width, (x) => updateRoom(r.id, { x }))}
              {number('Y', r.y, 120, 3900 - r.depth, (y) => updateRoom(r.id, { y }))}
              {number('Ancho', r.width, 200, 1140 - r.x, (width) => updateRoom(r.id, { width }))}
              {number('Fondo', r.depth, 200, 3900 - r.y, (depth) => updateRoom(r.id, { depth }))}
            </div>
            <label>
              Puerta
              <select
                aria-label="Puerta"
                value={r.door}
                onChange={(e) => updateRoom(r.id, { door: e.target.value as Room['door'] })}
              >
                <option value="top">Arriba</option>
                <option value="bottom">Abajo</option>
                <option value="left">Izquierda</option>
                <option value="right">Derecha</option>
              </select>
            </label>
            <button
              onClick={() =>
                onChange({ ...value, rooms: value.rooms.filter((item) => item.id !== r.id) })
              }
            >
              Eliminar sala
            </button>
          </fieldset>
        ))}
        {value.partitions.map((p, i) => (
          <fieldset key={p.id}>
            <legend>División {i + 1}</legend>
            <label>
              Orientación
              <select
                aria-label="Orientación"
                value={p.orientation}
                onChange={(e) => {
                  const orientation = e.target.value as Partition['orientation'];
                  const x = orientation === 'horizontal' ? Math.min(p.x, 980) : p.x;
                  const y = orientation === 'vertical' ? Math.min(p.y, 3740) : p.y;
                  updatePartition(p.id, {
                    orientation,
                    x,
                    y,
                    length: Math.min(p.length, orientation === 'horizontal' ? 1140 - x : 3900 - y),
                  });
                }}
              >
                <option value="horizontal">Horizontal</option>
                <option value="vertical">Vertical</option>
              </select>
            </label>
            <div className="floorplan-fields">
              {number('X', p.x, 60, p.orientation === 'horizontal' ? 1140 - p.length : 1140, (x) =>
                updatePartition(p.id, { x }),
              )}
              {number('Y', p.y, 120, p.orientation === 'vertical' ? 3900 - p.length : 3800, (y) =>
                updatePartition(p.id, { y }),
              )}
              {number(
                'Largo',
                p.length,
                160,
                p.orientation === 'horizontal' ? 1140 - p.x : 3900 - p.y,
                (length) => updatePartition(p.id, { length }),
              )}
            </div>
            <label>
              <input
                type="checkbox"
                checked={p.doorway}
                onChange={(e) => updatePartition(p.id, { doorway: e.target.checked })}
              />
              Con puerta central
            </label>
            <button
              onClick={() =>
                onChange({
                  ...value,
                  partitions: value.partitions.filter((item) => item.id !== p.id),
                })
              }
            >
              Eliminar división
            </button>
          </fieldset>
        ))}
      </div>
    </fieldset>
  );
}

export function FloorplanLayer({
  value,
  onChange,
  disabled,
  editing,
}: Props & { editing: boolean }) {
  const drag = useRef<{ id: string; x: number; y: number } | null>(null);
  const coordinates = (e: PointerEvent<SVGGElement>) => {
    const matrix = e.currentTarget.ownerSVGElement?.getScreenCTM();
    return matrix ? new DOMPoint(e.clientX, e.clientY).matrixTransform(matrix.inverse()) : null;
  };
  function handlers(item: Room | Partition, room: boolean) {
    const move = (x: number, y: number) => {
      const width = room
        ? (item as Room).width
        : (item as Partition).orientation === 'horizontal'
          ? (item as Partition).length
          : 0;
      const depth = room
        ? (item as Room).depth
        : (item as Partition).orientation === 'vertical'
          ? (item as Partition).length
          : 0;
      const patch = {
        x: Math.max(60, Math.min(1140 - width, snap(x))),
        y: Math.max(120, Math.min(Math.min(3800, 3900 - depth), snap(y))),
      };
      onChange(
        room
          ? { ...value, rooms: value.rooms.map((r) => (r.id === item.id ? { ...r, ...patch } : r)) }
          : {
              ...value,
              partitions: value.partitions.map((p) => (p.id === item.id ? { ...p, ...patch } : p)),
            },
      );
    };
    return {
      onPointerDown: (e: PointerEvent<SVGGElement>) => {
        if (!editing || disabled) return;
        const p = coordinates(e);
        if (!p) return;
        drag.current = { id: item.id, x: p.x - item.x, y: p.y - item.y };
        e.currentTarget.setPointerCapture(e.pointerId);
      },
      onPointerMove: (e: PointerEvent<SVGGElement>) => {
        if (disabled || drag.current?.id !== item.id) return;
        const p = coordinates(e);
        if (p) move(p.x - drag.current.x, p.y - drag.current.y);
      },
      onPointerUp: () => {
        drag.current = null;
      },
      onPointerCancel: () => {
        drag.current = null;
      },
      onLostPointerCapture: () => {
        drag.current = null;
      },
      onKeyDown: (e: KeyboardEvent<SVGGElement>) => {
        if (!editing || disabled) return;
        const delta: Record<string, [number, number]> = {
          ArrowLeft: [-20, 0],
          ArrowRight: [20, 0],
          ArrowUp: [0, -20],
          ArrowDown: [0, 20],
        };
        if (delta[e.key]) {
          e.preventDefault();
          move(item.x + delta[e.key][0], item.y + delta[e.key][1]);
        }
      },
    };
  }
  return (
    <g className={editing ? 'floorplan-layer editing' : 'floorplan-layer'}>
      {value.rooms.map((r) => (
        <g
          key={r.id}
          {...handlers(r, true)}
          tabIndex={editing ? 0 : undefined}
          role={editing ? 'button' : undefined}
          aria-label={`Sala ${r.name}`}
        >
          <rect
            x={r.x}
            y={r.y}
            width={r.width}
            height={r.depth}
            fill="#d8e7e8"
            fillOpacity={0.65}
          />
          {wallsOf({ rooms: [r], partitions: [] }).map((w, i) => (
            <line
              key={i}
              x1={w.a.x}
              y1={w.a.y}
              x2={w.b.x}
              y2={w.b.y}
              stroke="#52767b"
              strokeWidth={10}
            />
          ))}
          <text x={r.x + 14} y={r.y + 26} fill="#294e56" fontSize={18} fontWeight={600}>
            {r.name}
          </text>
        </g>
      ))}
      {value.partitions.map((p, index) => (
        <g
          key={p.id}
          {...handlers(p, false)}
          tabIndex={editing ? 0 : undefined}
          role={editing ? 'button' : undefined}
          aria-label={`División ${index + 1}`}
        >
          {editing && (
            <line
              x1={p.x}
              y1={p.y}
              x2={p.x + (p.orientation === 'horizontal' ? p.length : 0)}
              y2={p.y + (p.orientation === 'vertical' ? p.length : 0)}
              stroke="transparent"
              strokeWidth={32}
            />
          )}
          {wallsOf({ rooms: [], partitions: [p] }).map((w, i) => (
            <line
              key={i}
              x1={w.a.x}
              y1={w.a.y}
              x2={w.b.x}
              y2={w.b.y}
              stroke="#8a7968"
              strokeWidth={10}
            />
          ))}
        </g>
      ))}
    </g>
  );
}
