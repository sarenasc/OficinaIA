import { describe, expect, it } from 'vitest';
import { graphPositions } from './officeGraphLayout';

describe('organigrama', () => {
  it('separa seis agentes importados en el mismo puesto', () => {
    const agents = Array.from({ length: 6 }, (_, index) => ({
      id: String(index),
      position: { x: 100, y: 100 },
    }));
    const result = graphPositions(agents);
    expect(new Set(result.map((a) => `${a.position.x},${a.position.y}`)).size).toBe(6);
    expect(result).toEqual(graphPositions(agents));
    expect(agents.every((a) => a.position.x === 100 && a.position.y === 100)).toBe(true);
  });
  it('conserva las posiciones separadas que el usuario eligió', () => {
    const agents = [
      { id: 'a', position: { x: -500, y: 20 } },
      { id: 'b', position: { x: 600, y: 450 } },
    ];
    expect(graphPositions(agents)).toEqual(agents);
  });
});
