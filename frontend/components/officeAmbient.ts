import type { Point } from './officePaths';

export function canRoam(status: string, connected: boolean, reducedMotion: boolean) {
  return status === 'active' && connected && !reducedMotion;
}
export function restDestination(index: number, phase: number, height: number): Point {
  const destinations = [
    { x: 180, y: height - 310 },
    { x: 550, y: height - 150 },
    { x: 960, y: height - 320 },
  ];
  return destinations[(index + phase) % destinations.length];
}
