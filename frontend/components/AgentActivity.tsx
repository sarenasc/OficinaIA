import type { Row } from '../api';
import { Status } from './Status';

const operations: Record<string, string> = {
  'sql.describe': 'Consultando estructura SQL',
  'social.prepare_post': 'Preparando borrador de publicación',
  'excel.create': 'Creando Excel', 'excel.generate_sales': 'Generando ventas ficticias',
  'excel.from_csv': 'Convirtiendo CSV a Excel', 'sql.export_excel': 'Creando reporte SQL', 'filesystem.list': 'Consultando carpeta', 'excel.read': 'Leyendo Excel',
  'csv.read': 'Leyendo CSV', 'filesystem.read': 'Leyendo archivo',
  'filesystem.write': 'Escribiendo archivo', 'filesystem.create_directory': 'Creando carpeta',
  'data.summarize': 'Analizando datos', 'python.execute': 'Ejecutando Python',
  'sql.query': 'Consultando base de datos',
};
export function AgentActivity({ agent, onTask }: { agent: Row; onTask: (id: string) => void }) {
  const activity = agent.activity;
  if (!activity) return <p className="muted">Sin tareas registradas.</p>;
  const running = activity.execution_status === 'running' || activity.execution_status === 'pending';
  const label = activity.tool ? operations[activity.tool] || activity.tool :
    activity.execution_status ? 'Consultando modelo IA' : 'Preparando tarea';
  return <div className="agent-activity-detail">
    <p><strong>{running ? label : `Última operación: ${label}`}</strong></p>
    {activity.resource && <p>Recurso: {activity.resource}</p>}
    {activity.path && <p className="activity-path">Archivo: {activity.path}</p>}
    <p className="activity-request">{activity.request}</p>
    <Status value={activity.task_status} />
    {activity.error && <p className="activity-error"><strong>Error: </strong>{activity.error}</p>}
    <button onClick={() => onTask(activity.task_id)}>Abrir tarea</button>
  </div>;
}
