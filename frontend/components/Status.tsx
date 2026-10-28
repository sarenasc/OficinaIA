export function Status({ value }: { value: string }) {
  const map: Record<string, string> = {
    active: 'Activo',
    disabled: 'Desactivado',
    pending: 'Pendiente',
    executing: 'Ejecutando',
    working: 'Trabajando',
    waiting: 'Esperando',
    waiting_approval: 'Esperando aprobación',
    completed: 'Completada',
    error: 'Error',
    cancelled: 'Cancelada',
    running: 'Ejecutando',
  };
  return <span className={'status ' + value}>{map[value] || value}</span>;
}
