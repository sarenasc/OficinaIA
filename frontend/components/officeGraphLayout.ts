export function graphPositions(agents: { id: string; position?: { x: number; y: number } }[]) {
  const occupied: { x: number; y: number }[] = [];
  return agents.map((agent) => {
    let position = agent.position || { x: 100, y: 100 };
    const collides = (point: { x: number; y: number }) =>
      occupied.some((p) => Math.abs(p.x - point.x) < 250 && Math.abs(p.y - point.y) < 210);
    if (collides(position)) {
      let index = 0;
      do {
        position = { x: 100 + (index % 3) * 300, y: 100 + Math.floor(index / 3) * 240 };
        index++;
      } while (collides(position));
    }
    occupied.push(position);
    return { id: agent.id, position };
  });
}
