import type { Point } from './officePaths';

export type Room = {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  depth: number;
  door: 'top' | 'bottom' | 'left' | 'right';
};
export type Partition = {
  id: string;
  x: number;
  y: number;
  length: number;
  orientation: 'horizontal' | 'vertical';
  doorway: boolean;
};
export type Structure = { rooms: Room[]; partitions: Partition[] };
export type Wall = { a: Point; b: Point };
export const EMPTY_STRUCTURE: Structure = { rooms: [], partitions: [] };
export const snap = (value: number) => Math.round(value / 20) * 20;

export function wallsOf(structure: Structure): Wall[] {
  const walls: Wall[] = [];
  function wall(x: number, y: number, length: number, horizontal: boolean, door: boolean) {
    const p = (n: number): Point => ({ x: x + (horizontal ? n : 0), y: y + (horizontal ? 0 : n) });
    if (door) {
      walls.push({ a: p(0), b: p(length / 2 - 50) }, { a: p(length / 2 + 50), b: p(length) });
    } else walls.push({ a: p(0), b: p(length) });
  }
  for (const r of structure.rooms) {
    wall(r.x, r.y, r.width, true, r.door === 'top');
    wall(r.x, r.y + r.depth, r.width, true, r.door === 'bottom');
    wall(r.x, r.y, r.depth, false, r.door === 'left');
    wall(r.x + r.width, r.y, r.depth, false, r.door === 'right');
  }
  for (const p of structure.partitions)
    wall(p.x, p.y, p.length, p.orientation === 'horizontal', p.doorway);
  return walls;
}

export function crossesWall(a: Point, b: Point, walls: Wall[]): boolean {
  return walls.some(
    (w) =>
      Math.max(a.x, b.x) >= Math.min(w.a.x, w.b.x) - 12 &&
      Math.min(a.x, b.x) <= Math.max(w.a.x, w.b.x) + 12 &&
      Math.max(a.y, b.y) >= Math.min(w.a.y, w.b.y) - 12 &&
      Math.min(a.y, b.y) <= Math.max(w.a.y, w.b.y) + 12,
  );
}

export function structureHeight(s: Structure): number {
  return Math.max(
    900,
    ...s.rooms.map((r) => r.y + r.depth + 100),
    ...s.partitions.map((p) => p.y + (p.orientation === 'vertical' ? p.length : 0) + 100),
  );
}
