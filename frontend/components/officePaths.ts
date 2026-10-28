export type Point = { x: number; y: number };
export const defaultPosition = (index: number): Point => ({
  x: 220 + (index % 4) * 250,
  y: 200 + Math.floor(index / 4) * 240,
});
export const clampPosition = (point: Point): Point => ({
  x: Math.max(100, Math.min(1100, point.x)),
  y: Math.max(130, Math.min(3800, point.y)),
});

// A grid route keeps a visiting character out of desk tops and within the room.
export function walkingRoute(start: Point, end: Point, desks: Point[], height: number): Point[] {
  const step = 20;
  const cell = (p: Point) => ({ x: Math.round(p.x / step), y: Math.round(p.y / step) });
  const key = (p: Point) => `${p.x},${p.y}`;
  const from = cell(start),
    to = cell(end);
  const queue = [from];
  const previous = new Map<string, Point | null>([[key(from), null]]);
  let cursor = 0;
  while (cursor < queue.length) {
    const current = queue[cursor++];
    if (key(current) === key(to)) {
      const route: Point[] = [];
      let point: Point | null = current;
      while (point) {
        route.push({ x: point.x * step, y: point.y * step });
        point = previous.get(key(point)) || null;
      }
      route.reverse();
      return [start, ...route, end];
    }
    for (const delta of [
      { x: 1, y: 0 },
      { x: -1, y: 0 },
      { x: 0, y: 1 },
      { x: 0, y: -1 },
    ]) {
      const next = { x: current.x + delta.x, y: current.y + delta.y };
      const px = next.x * step,
        py = next.y * step;
      if (px < 55 || px > 1140 || py < 120 || py > height - 70 || previous.has(key(next))) continue;
      if (desks.some((d) => Math.abs(px - d.x) < 115 && py > d.y - 100 && py < d.y + 110)) continue;
      previous.set(key(next), current);
      queue.push(next);
    }
  }
  return [];
}

export function routePosition(route: Point[], distance: number): Point {
  for (let index = 1; index < route.length; index++) {
    const a = route[index - 1],
      b = route[index],
      length = Math.hypot(b.x - a.x, b.y - a.y);
    if (distance <= length)
      return {
        x: a.x + (b.x - a.x) * (length ? distance / length : 0),
        y: a.y + (b.y - a.y) * (length ? distance / length : 0),
      };
    distance -= length;
  }
  return route[route.length - 1];
}
