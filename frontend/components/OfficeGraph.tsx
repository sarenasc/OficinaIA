import { useEffect, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  applyNodeChanges,
  BaseEdge,
  getBezierPath,
  type EdgeProps,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { api, type Row } from '../api';
import { Status } from './Status';
import { graphPositions } from './officeGraphLayout';

type DelegationEdge = Edge<{ color: string; direction: string; enabled: boolean }>;

function FlowEdge({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  markerEnd, data, style }: EdgeProps<DelegationEdge>) {
  const [path] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition });
  return <g>
    <title>{data?.direction}</title>
    <BaseEdge path={path} markerEnd={markerEnd} style={style} interactionWidth={24} />
    {data?.enabled && <circle className="delegation-flow-dot" r={4.5} fill={data.color} stroke="#fff" strokeWidth={1.5} pointerEvents="none">
      <animateMotion path={path} dur="3s" repeatCount="indefinite" />
    </circle>}
  </g>;
}

const edgeTypes = { delegation: FlowEdge };

export function OfficeGraph({
  agents,
  relations,
  onEdit,
  onAction,
  refresh,
}: {
  agents: Row[];
  relations: Row[];
  onEdit: (row: Row) => void;
  onAction: (action: () => Promise<any>) => Promise<any>;
  refresh: () => Promise<void>;
}) {
  const makeNodes = () => {
    const positions = graphPositions(agents.map(a => ({ id: a.id, position: a.position })));
    return agents.map((a, index) => ({
      id: a.id,
      position: positions[index].position,
      data: {
        label: (
          <div>
            <strong>{a.name}</strong>
            <small>{a.role || a.goal}</small>
            <Status value={a.status} />
          </div>
        ),
      },
      style: { width: 210 },
    }));
  };
  const [nodes, setNodes] = useState<Node[]>(makeNodes);
  const dragging = useRef(false);
  useEffect(() => {
    if (!dragging.current) setNodes(makeNodes());
  }, [agents]);
  const edges: Edge[] = relations
    .filter(
      (r) => agents.some((a) => a.id === r.source_id) && agents.some((a) => a.id === r.target_id),
    )
    .map((r) => {
      const source = agents.find(a => a.id === r.source_id)!;
      const target = agents.find(a => a.id === r.target_id)!;
      const enabled = source.status !== 'disabled' && target.status !== 'disabled';
      const color = !enabled ? '#7b8796' : target.status === 'working' ? '#c26b08' : '#087f9c';
      const direction = `${source.name} delega a ${target.name}`;
      return {
        id: r.id,
        type: 'delegation',
        source: r.source_id,
        target: r.target_id,
        ariaLabel: direction,
        data: { color, direction, enabled },
        style: { stroke: color, strokeWidth: 3, strokeDasharray: enabled ? undefined : '6 5' },
        markerEnd: { type: MarkerType.ArrowClosed, color, width: 24, height: 24 },
      };
    });
  return (
    <section>
      <div className="graph-flow-legend" aria-label="Leyenda del flujo de delegación">
        <span><b className="graph-flow-blue" aria-hidden="true">● →</b> Dirección de delegación</span>
        <span><b className="graph-flow-orange" aria-hidden="true">● →</b> Destinatario trabajando</span>
        <span><b className="graph-flow-gray" aria-hidden="true">⇢</b> Agente desactivado</span>
      </div>
      <p className="muted">
        Los puntos viajan desde quien delega hacia quien recibe. Conecta desde la salida inferior
        del coordinador a la entrada superior del especialista. Arrastra puestos para moverlos. Doble clic abre
        configuración. Doble clic sobre relación permite eliminarla.
      </p>
      <div className="graph">
        <ReactFlow
          nodes={nodes}
          onNodeDragStart={() => {
            dragging.current = true;
          }}
          edges={edges}
          edgeTypes={edgeTypes}
          onNodesChange={(changes) => setNodes((old) => applyNodeChanges(changes, old))}
          deleteKeyCode={null}
          onNodeDragStop={(_, node) =>
            void onAction(async () => {
              dragging.current = false;
              await api(`agents/${node.id}`, 'PATCH', {
                position: node.position,
              });
              await refresh();
            })
          }
          onConnect={(connection) =>
            void onAction(async () => {
              await api('relations', 'POST', {
                source_id: connection.source,
                target_id: connection.target,
              });
              await refresh();
            })
          }
          onNodeDoubleClick={(_, node) => {
            const agent = agents.find((a) => a.id === node.id);
            if (agent) onEdit(agent);
          }}
          onEdgeDoubleClick={(_, edge) => {
            if (confirm('¿Eliminar relación?'))
              void onAction(async () => {
                await api(`relations/${edge.id}`, 'DELETE');
                await refresh();
              });
          }}
          fitView
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    </section>
  );
}
