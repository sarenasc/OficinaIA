import { useEffect, useRef, useState, type ReactNode } from 'react';
import { routePosition, walkingRoute, type Point } from './officePaths';
import type { Wall } from './floorplan';

export function OfficeWalker({
  eventId,
  destination,
  home,
  obstacles,
  walls,
  height,
  paused,
  children,
}: {
  eventId?: string;
  destination?: Point;
  home: Point;
  obstacles: Point[];
  walls: Wall[];
  height: number;
  paused: boolean;
  children: ReactNode;
}) {
  const [offset, setOffset] = useState<Point>({ x: 0, y: 0 });
  const [walking, setWalking] = useState(false);
  const seen = useRef<string | undefined>(eventId);
  const pause = useRef(paused);
  pause.current = paused;
  // Coordinates are captured per event; REST/heartbeat rerenders never restart a walk.
  const current = useRef({ destination, home, obstacles, height, walls });
  current.current = { destination, home, obstacles, height, walls };
  useEffect(() => {
    if (!eventId || seen.current === eventId) return;
    seen.current = eventId;
    const { destination, home, obstacles, height, walls } = current.current;
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (!destination || motion.matches) return;
    const seat = { x: home.x, y: home.y + 65 };
    const start = { x: home.x, y: home.y + 130 },
      end = { x: Math.min(1110, destination.x + 65), y: destination.y + 130 };
    const outward = walkingRoute(start, end, obstacles, height, walls);
    if (!outward.length) return;
    const visit = [seat, ...outward];
    const route = [...visit, ...visit.slice(0, -1).reverse()];
    const total = route
      .slice(1)
      .reduce((sum, p, i) => sum + Math.hypot(p.x - route[i].x, p.y - route[i].y), 0);
    let frame = 0,
      last = 0,
      distance = 0;
    setWalking(true);
    function animate(now: number) {
      if (motion.matches) {
        setOffset({ x: 0, y: 0 });
        setWalking(false);
        return;
      }
      if (last && !pause.current) distance += Math.min(now - last, 50) * 0.18;
      last = now;
      if (distance >= total) {
        setOffset({ x: 0, y: 0 });
        setWalking(false);
        return;
      }
      if (!pause.current) {
        const p = routePosition(route, distance);
        setOffset({ x: p.x - home.x, y: p.y - seat.y });
      }
      frame = requestAnimationFrame(animate);
    }
    frame = requestAnimationFrame(animate);
    return () => {
      cancelAnimationFrame(frame);
      setOffset({ x: 0, y: 0 });
      setWalking(false);
    };
  }, [eventId]);
  return (
    <g
      className={walking ? 'office-walker walking' : 'office-walker'}
      transform={`translate(${offset.x},${offset.y})`}
      data-walking={walking}
    >
      {children}
    </g>
  );
}
