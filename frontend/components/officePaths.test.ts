import { describe, expect, it } from 'vitest';
import { clampPosition, routePosition, walkingRoute } from './officePaths';

describe('recorridos en la oficina', () => {
  it('rodea escritorios y conecta los dos puestos', () => {
    const desks = [
      { x: 220, y: 200 },
      { x: 470, y: 200 },
      { x: 350, y: 300 },
    ];
    const start = { x: 220, y: 330 },
      end = { x: 470, y: 330 };
    const path = walkingRoute(start, end, desks, 650);
    expect(path[0]).toEqual(start);
    expect(path.at(-1)).toEqual(end);
    for (const point of path) {
      expect(
        desks.some(
          (d) => Math.abs(point.x - d.x) < 115 && point.y > d.y - 100 && point.y < d.y + 110,
        ),
      ).toBe(false);
    }
  });
  it('no atraviesa una barrera cerrada', () => {
    const barrier = Array.from({ length: 7 }, (_, i) => ({ x: 100 + i * 170, y: 300 }));
    expect(walkingRoute({ x: 200, y: 160 }, { x: 200, y: 450 }, barrier, 650)).toEqual([]);
  });
  it('limita el arrastre y recorre segmentos a velocidad uniforme', () => {
    expect(clampPosition({ x: -200, y: 5000 })).toEqual({ x: 100, y: 3800 });
    expect(
      routePosition(
        [
          { x: 0, y: 0 },
          { x: 100, y: 0 },
          { x: 100, y: 100 },
        ],
        150,
      ),
    ).toEqual({ x: 100, y: 50 });
  });
});
