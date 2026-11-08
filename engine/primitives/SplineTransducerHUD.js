import * as THREE from '../../assets/vendor/three.module.js';

export class SplineTransducerHUD {
  constructor(svgElement, camera, width = 3840, height = 2160) {
    this.svg = svgElement;
    this.camera = camera;
    this.width = width;
    this.height = height;
    this.tethers = new Map();
  }

  addTether(id, config = {}) {
    const {
      sourceX = 1000,
      sourceY = 300,
      target3D = new THREE.Vector3(0, 0, 0),
      color = '#00f0ff',
      label = '',
      unit = '',
      strokeWidth = 4
    } = config;

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', color);
    path.setAttribute('stroke-width', strokeWidth);
    path.setAttribute('stroke-dasharray', '12 6');
    this.svg.appendChild(path);

    this.tethers.set(id, {
      path,
      sourceX,
      sourceY,
      target3D,
      color,
      label,
      unit,
      struck: false
    });
  }

  setUnitStrikethrough(id, struck = true) {
    const tether = this.tethers.get(id);
    if (tether) {
      tether.struck = struck;
    }
  }

  update() {
    this.tethers.forEach((tether) => {
      const p = tether.target3D.clone().project(this.camera);
      const targetX = (p.x * 0.5 + 0.5) * this.width;
      const targetY = (-p.y * 0.5 + 0.5) * this.height;

      const cp1X = tether.sourceX + (targetX - tether.sourceX) * 0.4;
      const cp1Y = tether.sourceY + 40;
      const cp2X = targetX - 120;
      const cp2Y = targetY - 140;

      const d = `M ${tether.sourceX} ${tether.sourceY} C ${cp1X} ${cp1Y}, ${cp2X} ${cp2Y}, ${targetX} ${targetY}`;
      tether.path.setAttribute('d', d);
    });
  }
}
