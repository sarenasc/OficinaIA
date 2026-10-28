import * as THREE from 'three';
import type { Point } from './officePaths';

export type Person = {
  id: string;
  root: THREE.Group;
  leftLeg: THREE.Group;
  rightLeg: THREE.Group;
  leftArm: THREE.Group;
  rightArm: THREE.Group;
  shirt: THREE.MeshStandardMaterial;
  cup: THREE.Group;
  color: number;
  home: Point;
  location: Point;
  route: Point[];
  distance: number;
  phase: number;
  nextAt: number;
  status: string;
  label: THREE.Sprite;
};
export function createOfficeWorld(
  agents: { id: string; name: string }[],
  positions: Point[],
  height: number,
) {
  const world = new THREE.Group();
  const people: Person[] = [];
  const x = (value: number) => value / 60 - 10,
    z = (value: number) => value / 60 - height / 120;
  const mat = (color: number) => new THREE.MeshStandardMaterial({ color, roughness: 0.72 });
  function box(
    parent: THREE.Object3D,
    w: number,
    h: number,
    d: number,
    px: number,
    py: number,
    pz: number,
    color: number,
  ) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(color));
    mesh.position.set(px, py, pz);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    parent.add(mesh);
    return mesh;
  }
  function sphere(
    parent: THREE.Object3D,
    r: number,
    px: number,
    py: number,
    pz: number,
    color: number,
  ) {
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 12), mat(color));
    mesh.position.set(px, py, pz);
    mesh.castShadow = true;
    parent.add(mesh);
    return mesh;
  }
  function cylinder(
    parent: THREE.Object3D,
    top: number,
    bottom: number,
    h: number,
    px: number,
    py: number,
    pz: number,
    color: number,
  ) {
    const mesh = new THREE.Mesh(new THREE.CylinderGeometry(top, bottom, h, 16), mat(color));
    mesh.position.set(px, py, pz);
    mesh.castShadow = true;
    parent.add(mesh);
    return mesh;
  }
  function label(text: string, width = 3) {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 96;
    const context = canvas.getContext('2d')!;
    context.fillStyle = '#ffffffee';
    context.beginPath();
    context.roundRect(0, 0, 512, 96, 18);
    context.fill();
    context.fillStyle = '#24464d';
    context.font = '600 34px Segoe UI';
    context.textAlign = 'center';
    context.fillText(text.slice(0, 30), 256, 60);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, depthTest: false }));
    sprite.scale.set(width, (width * 96) / 512, 1);
    return sprite;
  }
  box(world, 20, 0.18, height / 60, 0, -0.09, 0, 0xd6c7ae);
  for (let i = 0; i < 20; i++) box(world, 0.012, 0.01, height / 60, -10 + i, 0.015, 0, 0xc1b299);
  box(world, 20, 0.02, 5, 0, 0.02, z(height - 170), 0xaebdb3);
  box(world, 20, 3.5, 0.18, 0, 1.75, -height / 120, 0xf0eee7);
  box(world, 0.18, 3.5, height / 60, -10, 1.75, 0, 0xe0e8e2);
  for (const px of [-6, 0, 6]) {
    box(world, 4.1, 1.75, 0.12, px, 2.15, -height / 120 + 0.15, 0xb2d9dd);
    box(world, 0.05, 1.75, 0.16, px, 2.15, -height / 120 + 0.24, 0xffffff);
    box(world, 4.25, 0.1, 0.4, px, 1.25, -height / 120 + 0.25, 0xffffff);
  }
  const officeSign = label('OFICINA · EQUIPO EN VIVO', 5);
  officeSign.position.set(0, 3.25, -height / 120 + 0.3);
  world.add(officeSign);
  function plant(px: number, pz: number) {
    cylinder(world, 0.3, 0.23, 0.5, px, 0.25, pz, 0xb78161);
    sphere(world, 0.48, px, 0.95, pz, 0x4d885d);
    sphere(world, 0.32, px - 0.22, 1.2, pz, 0x71a47c);
  }
  plant(-9, height / 120 - 1);
  plant(9, height / 120 - 1);
  plant(9, -height / 120 + 1);
  const obstacles = [
    ...positions,
    { x: 160, y: height - 170 },
    { x: 550, y: height - 280 },
    { x: 980, y: height - 150 },
  ];
  // Cafeteria: cabinet, espresso machine, grinder, mugs and shelving.
  const coffee = new THREE.Group();
  coffee.position.set(x(160), 0, z(height - 170));
  world.add(coffee);
  box(coffee, 3.3, 1.05, 1.1, 0, 0.525, 0, 0x7a8d84);
  box(coffee, 3.45, 0.12, 1.25, 0, 1.12, 0, 0xe8ddc8);
  for (const px of [-1, 0, 1]) {
    box(coffee, 0.9, 0.8, 0.03, px, 0.55, 0.57, 0x93a49a);
    box(coffee, 0.25, 0.035, 0.07, px, 0.8, 0.61, 0xc6a776);
  }
  box(coffee, 0.95, 0.8, 0.65, -0.65, 1.57, 0, 0x333f43);
  box(coffee, 0.8, 0.25, 0.1, -0.65, 1.55, 0.39, 0xbcc8cb);
  box(coffee, 0.85, 0.045, 0.45, -0.65, 1.23, 0.24, 0x171f21);
  cylinder(coffee, 0.045, 0.045, 0.18, -0.82, 1.4, 0.4, 0xc5ccd0);
  cylinder(coffee, 0.045, 0.045, 0.18, -0.5, 1.4, 0.4, 0xc5ccd0);
  cylinder(coffee, 0.12, 0.12, 0.23, -0.82, 1.3, 0.39, 0xffffff);
  cylinder(coffee, 0.12, 0.12, 0.23, -0.5, 1.3, 0.39, 0xe9b284);
  cylinder(coffee, 0.22, 0.22, 0.35, 0.62, 1.4, 0, 0x544a3e);
  cylinder(coffee, 0.2, 0.16, 0.32, 0.62, 1.73, 0, 0xb99574);
  for (let i = 0; i < 3; i++)
    cylinder(coffee, 0.12, 0.1, 0.22, 1.1, 1.25 + i * 0.17, 0.1, 0xe7ede7);
  const coffeeSign = label('CAFETERÍA · CAFÉ', 3.4);
  coffeeSign.position.set(x(160), 2.5, z(height - 170));
  world.add(coffeeSign);
  // Dining table and chairs.
  const table = new THREE.Group();
  table.position.set(x(550), 0, z(height - 280));
  world.add(table);
  box(table, 2.8, 0.13, 1.5, 0, 1.05, 0, 0xc09163);
  for (const px of [-1.1, 1.1])
    for (const pz of [-0.55, 0.55]) box(table, 0.09, 1, 0.09, px, 0.5, pz, 0x465552);
  for (const px of [-0.8, 0.8])
    for (const pz of [-1.2, 1.2]) {
      box(table, 0.65, 0.12, 0.65, px, 0.57, pz, 0x7d9c8d);
      box(table, 0.65, 0.7, 0.1, px, 0.95, pz + Math.sign(pz) * 0.27, 0x7d9c8d);
      box(table, 0.12, 0.55, 0.12, px, 0.27, pz, 0x465552);
    }
  cylinder(table, 0.28, 0.28, 0.04, 0, 1.16, 0, 0xfaf4e6);
  sphere(table, 0.12, 0, 1.3, 0, 0xc48652);
  const diningSign = label('COMEDOR', 2.2);
  diningSign.position.set(x(550), 2.25, z(height - 280));
  world.add(diningSign);
  // Rest area: sofa, rug, low table and plant.
  box(world, 4.4, 0.025, 3.4, x(980), 0.04, z(height - 180), 0xd0a183);
  box(world, 3.6, 0.5, 1.15, x(980), 0.6, z(height - 150), 0x63868a);
  box(world, 3.6, 1.1, 0.25, x(980), 1.05, z(height - 125), 0x52787d);
  for (const px of [x(980) - 1.65, x(980) + 1.65])
    box(world, 0.3, 0.9, 1.3, px, 0.8, z(height - 150), 0x52787d);
  cylinder(world, 0.6, 0.6, 0.12, x(950), 0.55, z(height - 260), 0xc39d6e);
  cylinder(world, 0.12, 0.16, 0.5, x(950), 0.25, z(height - 260), 0x465552);
  const restSign = label('DESCANSO', 2.2);
  restSign.position.set(x(980), 2.25, z(height - 150));
  world.add(restSign);
  agents.forEach((agent, index) => {
    const p = positions[index];
    const desk = new THREE.Group();
    desk.position.set(x(p.x), 0, z(p.y));
    world.add(desk);
    box(desk, 3, 0.13, 1.5, 0, 1.15, 0, 0xc7a378);
    for (const px of [-1.3, 1.3])
      for (const pz of [-0.58, 0.58]) box(desk, 0.09, 1.1, 0.09, px, 0.55, pz, 0x64706d);
    box(desk, 1.2, 0.7, 0.08, 0, 1.62, -0.23, 0x2e414c);
    box(desk, 1.08, 0.56, 0.025, 0, 1.62, -0.175, 0x81b9c8);
    box(desk, 0.07, 0.3, 0.07, 0, 1.3, -0.23, 0x2e414c);
    box(desk, 0.8, 0.04, 0.25, 0, 1.25, 0.4, 0xe1e5e1);
    box(desk, 0.23, 0.03, 0.3, 0.75, 1.25, 0.35, 0x415b63);
    cylinder(desk, 0.11, 0.11, 0.22, -1.05, 1.31, 0.4, 0xf2eee2);
    box(desk, 0.85, 0.15, 0.8, 0, 0.65, 1.05, 0x485e68);
    box(desk, 0.85, 0.85, 0.12, 0, 1, 1.4, 0x485e68);
    cylinder(desk, 0.08, 0.08, 0.5, 0, 0.3, 1.05, 0x455252);
    const root = new THREE.Group();
    root.userData.agentId = agent.id;
    world.add(root);
    const colors = [0x557dc2, 0xb77391, 0x589782, 0xb78c57];
    const color = colors[index % 4];
    const torso = cylinder(root, 0.24, 0.3, 0.65, 0, 1.05, 0, color);
    const shirt = torso.material as THREE.MeshStandardMaterial;
    sphere(root, 0.23, 0, 1.65, 0, 0xe2b28e);
    sphere(root, 0.235, 0, 1.76, -0.035, 0x514036);
    sphere(root, 0.035, -0.07, 1.67, 0.208, 0x29383c);
    sphere(root, 0.035, 0.07, 1.67, 0.208, 0x29383c);
    const limb = (px: number, py: number, length: number, color: number) => {
      const group = new THREE.Group();
      group.position.set(px, py, 0);
      root.add(group);
      box(group, 0.13, length, 0.15, 0, -length / 2, 0, color);
      return group;
    };
    const leftLeg = limb(-0.14, 0.78, 0.7, 0x334b60),
      rightLeg = limb(0.14, 0.78, 0.7, 0x334b60);
    box(leftLeg, 0.18, 0.12, 0.3, 0, -0.68, 0.07, 0x263740);
    box(rightLeg, 0.18, 0.12, 0.3, 0, -0.68, 0.07, 0x263740);
    const leftArm = limb(-0.32, 1.32, 0.55, 0xe2b28e),
      rightArm = limb(0.32, 1.32, 0.55, 0xe2b28e);
    const cup = new THREE.Group();
    cup.position.set(0, -0.54, 0.04);
    rightArm.add(cup);
    cylinder(cup, 0.11, 0.1, 0.2, 0, 0, 0, 0xf4ede0);
    cup.visible = false;
    const name = label(agent.name, 2.6);
    name.position.y = 2.2;
    root.add(name);
    people.push({
      id: agent.id,
      root,
      leftLeg,
      rightLeg,
      leftArm,
      rightArm,
      shirt,
      cup,
      color,
      home: p,
      location: { x: p.x, y: p.y + 130 },
      route: [],
      distance: 0,
      phase: 0,
      nextAt: 1000 + index * 1500,
      status: '',
      label: name,
    });
  });
  function dispose() {
    world.traverse((object) => {
      if (object instanceof THREE.Mesh) object.geometry.dispose();
      const material = (object as THREE.Mesh).material;
      if (material) {
        for (const item of Array.isArray(material) ? material : [material]) {
          const map = (item as THREE.MeshStandardMaterial).map;
          map?.dispose();
          item.dispose();
        }
      }
    });
  }
  return { world, people, obstacles, x, z, dispose };
}
