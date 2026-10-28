import { describe, expect, it } from 'vitest';
import { canRoam, restDestination } from './officeAmbient';

describe('ambientación de oficina', () => {
  it('solo permite pasear a agentes disponibles con conexión y movimiento habilitado', () => {
    expect(canRoam('active', true, false)).toBe(true);
    for (const state of ['working', 'waiting', 'error', 'disabled'])
      expect(canRoam(state, true, false)).toBe(false);
    expect(canRoam('active', false, false)).toBe(false);
    expect(canRoam('active', true, true)).toBe(false);
  });
  it('alterna destinos de descanso dentro del espacio de la sala', () => {
    const targets = [0, 1, 2].map((phase) => restDestination(0, phase, 900));
    expect(new Set(targets.map((point) => `${point.x},${point.y}`)).size).toBe(3);
    for (const point of targets) {
      expect(point.x).toBeGreaterThan(50);
      expect(point.x).toBeLessThan(1150);
      expect(point.y).toBeLessThan(830);
    }
  });
});
