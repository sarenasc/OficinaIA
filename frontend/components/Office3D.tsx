import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { Row } from '../api';
import { createOfficeWorld } from './officeWorld';
import { canRoam, restDestination } from './officeAmbient';
import { routePosition, walkingRoute, type Point } from './officePaths';

export default function Office3D({
  agents,
  positions,
  connected,
  onSelect,
  onFallback,
}: {
  agents: Row[];
  positions: Point[];
  connected: boolean;
  onSelect: (id: string) => void;
  onFallback: () => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const latest = useRef({ agents, connected });
  latest.current = { agents, connected };
  const [error, setError] = useState('');
  const height = Math.max(900, ...positions.map((p) => p.y + 500));
  const layout = JSON.stringify(positions);
  const identity = agents.map((a) => `${a.id}:${a.name}`).join('|');
  useEffect(() => {
    if (!host.current) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    } catch {
      setError('Este equipo no pudo iniciar WebGL. Puedes seguir usando la oficina 2D.');
      return;
    }
    setError('');
    const container = host.current;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.setClearColor(0xe5ece7);
    container.appendChild(renderer.domElement);
    renderer.domElement.setAttribute(
      'aria-label',
      'Oficina 3D con escritorios, cafetería y descanso',
    );
    renderer.domElement.setAttribute('role', 'img');
    const scene = new THREE.Scene();
    const world = createOfficeWorld(
      latest.current.agents.map((agent) => ({ id: agent.id, name: agent.name })),
      JSON.parse(layout),
      height,
    );
    scene.add(world.world);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x748779, 2));
    const light = new THREE.DirectionalLight(0xfff4dc, 3);
    light.position.set(4, 15, 8);
    light.castShadow = true;
    light.shadow.mapSize.set(1024, 1024);
    light.shadow.camera.left = -15;
    light.shadow.camera.right = 15;
    light.shadow.camera.top = 15;
    light.shadow.camera.bottom = -15;
    scene.add(light);
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 150);
    camera.position.set(15, 17, 19);
    camera.lookAt(0, 0, 0);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0.3, 0);
    controls.enableDamping = true;
    controls.minDistance = 13;
    controls.maxDistance = 70;
    controls.maxPolarAngle = Math.PI * 0.47;
    controls.minPolarAngle = 0.2;
    const resize = new ResizeObserver(() => {
      const width = container.clientWidth,
        height = container.clientHeight;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    });
    resize.observe(container);
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const ray = new THREE.Raycaster();
    let pointerStart = { x: 0, y: 0 };
    const down = (event: PointerEvent) => {
      pointerStart = { x: event.clientX, y: event.clientY };
    };
    const pick = (event: PointerEvent) => {
      if (Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) > 6) return;
      const bounds = renderer.domElement.getBoundingClientRect();
      ray.setFromCamera(
        new THREE.Vector2(
          ((event.clientX - bounds.left) / bounds.width) * 2 - 1,
          (-(event.clientY - bounds.top) / bounds.height) * 2 + 1,
        ),
        camera,
      );
      const hit = ray.intersectObjects(
        world.people.map((p) => p.root),
        true,
      )[0];
      let item: THREE.Object3D | undefined = hit?.object;
      while (item) {
        if (item.userData.agentId) {
          onSelect(item.userData.agentId);
          break;
        }
        item = item.parent || undefined;
      }
    };
    renderer.domElement.addEventListener('pointerdown', down);
    renderer.domElement.addEventListener('pointerup', pick);
    let frame = 0,
      last = 0,
      elapsed = 0;
    function animate(now: number) {
      frame = requestAnimationFrame(animate);
      if (last && now - last < 33) return;
      const delta = last ? Math.min(now - last, 50) : 0;
      last = now;
      if (latest.current.connected && !motion.matches) elapsed += delta;
      for (const person of world.people) {
        const agent = latest.current.agents.find((a) => a.id === person.id);
        if (!agent) continue;
        const status = agent.status;
        const roam = canRoam(status, latest.current.connected, motion.matches);
        const seat = { x: person.home.x, y: person.home.y + 65 },
          anchor = { x: person.home.x, y: person.home.y + 130 };
        if (status !== person.status) {
          person.status = status;
          person.route = [];
          person.distance = 0;
          person.cup.visible = false;
          if (status === 'active') {
            person.location = anchor;
            person.nextAt = elapsed + 1500;
          } else if (status === 'working' && latest.current.connected && !motion.matches) {
            const route = walkingRoute(person.location, anchor, world.obstacles, height);
            person.route = route.length ? [...route, seat] : [];
            if (!route.length) person.location = seat;
          } else person.location = seat;
        }
        if (roam && !person.route.length && elapsed >= person.nextAt) {
          if (Math.hypot(person.location.x - seat.x, person.location.y - seat.y) < 2)
            person.location = anchor;
          const target =
            person.phase % 4 === 3
              ? anchor
              : restDestination(world.people.indexOf(person), person.phase, height);
          person.phase++;
          person.route = walkingRoute(person.location, target, world.obstacles, height);
          person.distance = 0;
          person.nextAt = elapsed + 8000;
        }
        const moving = person.route.length > 0 && latest.current.connected && !motion.matches;
        if (moving) {
          const previous = person.location;
          person.distance += delta * 0.13;
          person.location = routePosition(person.route, person.distance);
          const dx = person.location.x - previous.x,
            dz = person.location.y - previous.y;
          if (Math.hypot(dx, dz) > 0.1) person.root.rotation.y = Math.atan2(dx, dz);
          const total = person.route
            .slice(1)
            .reduce(
              (sum, p, i) => sum + Math.hypot(p.x - person.route[i].x, p.y - person.route[i].y),
              0,
            );
          if (person.distance >= total) {
            person.route = [];
            person.nextAt = elapsed + 5000 + (world.people.indexOf(person) % 3) * 1500;
            person.cup.visible = roam && person.location.x < 300;
          }
        }
        if (motion.matches) {
          person.route = [];
          person.location = seat;
          person.cup.visible = false;
        }
        const swing = moving ? Math.sin(elapsed * 0.016) * 0.5 : 0;
        person.leftLeg.rotation.x = swing;
        person.rightLeg.rotation.x = -swing;
        const typing =
          status === 'working' && !moving && latest.current.connected && !motion.matches;
        person.leftArm.rotation.x = typing ? -1 + Math.sin(elapsed * 0.015) * 0.12 : -swing * 0.65;
        person.rightArm.rotation.x = person.cup.visible
          ? -1
          : typing
            ? -1 - Math.sin(elapsed * 0.015) * 0.12
            : swing * 0.65;
        if (!moving && status !== 'active') person.root.rotation.y = Math.PI;
        person.shirt.color.set(
          status === 'error'
            ? 0xbc5757
            : status === 'disabled'
              ? 0x969d9b
              : status === 'waiting'
                ? 0xc49a51
                : person.color,
        );
        person.root.position.set(
          world.x(person.location.x),
          moving ? Math.abs(Math.sin(elapsed * 0.016)) * 0.045 : 0,
          world.z(person.location.y),
        );
        renderer.domElement.dataset.moving = String(
          world.people.filter(
            (p) => p.route.length > 0 && latest.current.connected && !motion.matches,
          ).length,
        );
      }
      controls.update();
      renderer.render(scene, camera);
    }
    frame = requestAnimationFrame(animate);
    return () => {
      cancelAnimationFrame(frame);
      resize.disconnect();
      controls.dispose();
      renderer.domElement.removeEventListener('pointerdown', down);
      renderer.domElement.removeEventListener('pointerup', pick);
      world.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    };
  }, [identity, layout, height, onSelect]);
  return (
    <div className="office-3d">
      <p className="scene-instructions">
        Arrastra para girar · rueda para acercar · selecciona una persona. Los paseos y el café son
        ambientación de agentes disponibles.
      </p>
      {error ? (
        <p role="alert">
          {error}
          <button onClick={onFallback}>Abrir plano 2D</button>
        </p>
      ) : null}
      <div className="office-3d-canvas" ref={host} />
      <div className="office-3d-people" aria-label="Seleccionar agente 3D">
        {agents.map((agent) => (
          <button key={agent.id} onClick={() => onSelect(agent.id)}>
            {agent.name} ·{' '}
            {{
              active: 'Disponible',
              working: 'Trabajando',
              waiting: 'Esperando',
              error: 'Error',
              disabled: 'Deshabilitado',
            }[agent.status as string] || agent.status}
          </button>
        ))}
      </div>
    </div>
  );
}
