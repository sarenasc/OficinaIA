import type { Row } from '../api';
import { Status } from './Status';

export function TaskList({ rows, onOpen }: { rows: Row[]; onOpen: (id: string) => void }) {
  return (
    <section>
      <h2>Tareas y ejecuciones</h2>
      {rows.map((task) => (
        <button className="task-row" key={task.id} onClick={() => onOpen(task.id)}>
          <div>
            <strong>{task.number}</strong>
            <span>{task.request}</span>
          </div>
          <Status value={task.status} />
        </button>
      ))}
      {!rows.length && (
        <p>Todavía no hay tareas. Crea agentes, asigna sus capacidades y ejecuta una solicitud.</p>
      )}
    </section>
  );
}
