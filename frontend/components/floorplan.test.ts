import { describe, expect, it } from 'vitest';
import { crossesWall, wallsOf, type Structure } from './floorplan';
import { walkingRoute } from './officePaths';

describe('recorridos entre salas', () => {
  const structure: Structure = {
    rooms: [
      { id: 'meeting', name: 'Reuniones', x: 200, y: 160, width: 400, depth: 320, door: 'bottom' },
    ],
    partitions: [],
  };
  it('sale por la puerta y no atraviesa las paredes', () => {
    const walls = wallsOf(structure);
    const route = walkingRoute({ x: 400, y: 320 }, { x: 800, y: 600 }, [], 900, walls);
    expect(route.length).toBeGreaterThan(0);
    expect(route.slice(1).some((p, i) => crossesWall(route[i], p, walls))).toBe(false);
    expect(route.some((p) => p.y === 480 && p.x > 350 && p.x < 450)).toBe(true);
  });
  it('no inventa un paso cuando una división cierra todo el recorrido', () => {
    const walls = wallsOf({
      rooms: [],
      partitions: [
        { id: 'wall', x: 60, y: 400, length: 1080, orientation: 'horizontal', doorway: false },
      ],
    });
    expect(walkingRoute({ x: 400, y: 200 }, { x: 400, y: 600 }, [], 900, walls)).toEqual([]);
  });
  it('permite cruzar una división con puerta', () => {
    const walls = wallsOf({
      rooms: [],
      partitions: [
        { id: 'wall', x: 60, y: 400, length: 1080, orientation: 'horizontal', doorway: true },
      ],
    });
    const route = walkingRoute({ x: 400, y: 200 }, { x: 400, y: 600 }, [], 900, walls);
    expect(route.length).toBeGreaterThan(0);
    expect(route.slice(1).some((p, i) => crossesWall(route[i], p, walls))).toBe(false);
  });
});
