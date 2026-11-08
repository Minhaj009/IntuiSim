import * as THREE from '../../assets/vendor/three.module.js';

export class OctantClipper {
  static createOctantWedgeGeometry(radius = 0.58, segments = 32) {
    const geom = new THREE.BufferGeometry();
    const positions = [];
    const normals = [];
    const indices = [];

    const grid = [];
    for (let i = 0; i <= segments; i++) {
      const row = [];
      const u = i / segments;
      const theta = Math.PI * 0.5 + u * Math.PI * 0.5;
      const sinTheta = Math.sin(theta);
      const cosTheta = Math.cos(theta);

      for (let j = 0; j <= segments; j++) {
        const v = j / segments;
        const phi = Math.PI + v * Math.PI * 0.5;
        const sinPhi = Math.sin(phi);
        const cosPhi = Math.cos(phi);

        const x = radius * sinTheta * sinPhi;
        const y = radius * cosTheta;
        const z = radius * sinTheta * cosPhi;

        const norm = new THREE.Vector3(x, y, z).normalize();
        positions.push(x, y, z);
        normals.push(norm.x, norm.y, norm.z);
        row.push(positions.length / 3 - 1);
      }
      grid.push(row);
    }

    for (let i = 0; i < segments; i++) {
      for (let j = 0; j < segments; j++) {
        const a = grid[i][j];
        const b = grid[i + 1][j];
        const c = grid[i + 1][j + 1];
        const d = grid[i][j + 1];
        indices.push(a, b, d);
        indices.push(b, c, d);
      }
    }

    const cX = positions.length / 3;
    positions.push(0, 0, 0); normals.push(1, 0, 0);
    const ringX = [];
    for (let j = 0; j <= segments; j++) {
      const ang = Math.PI + (j / segments) * Math.PI * 0.5;
      positions.push(0, radius * Math.cos(ang), radius * Math.sin(ang));
      normals.push(1, 0, 0);
      ringX.push(positions.length / 3 - 1);
    }
    for (let j = 0; j < segments; j++) indices.push(cX, ringX[j + 1], ringX[j]);

    const cY = positions.length / 3;
    positions.push(0, 0, 0); normals.push(0, 1, 0);
    const ringY = [];
    for (let j = 0; j <= segments; j++) {
      const ang = Math.PI + (j / segments) * Math.PI * 0.5;
      positions.push(radius * Math.sin(ang), 0, radius * Math.cos(ang));
      normals.push(0, 1, 0);
      ringY.push(positions.length / 3 - 1);
    }
    for (let j = 0; j < segments; j++) indices.push(cY, ringY[j], ringY[j + 1]);

    const cZ = positions.length / 3;
    positions.push(0, 0, 0); normals.push(0, 0, 1);
    const ringZ = [];
    for (let j = 0; j <= segments; j++) {
      const ang = Math.PI + (j / segments) * Math.PI * 0.5;
      positions.push(radius * Math.sin(ang), radius * Math.cos(ang), 0);
      normals.push(0, 0, 1);
      ringZ.push(positions.length / 3 - 1);
    }
    for (let j = 0; j < segments; j++) indices.push(cZ, ringZ[j + 1], ringZ[j]);

    geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geom.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
    geom.setIndex(indices);
    return geom;
  }

  static createOuterSevenEighthsGeometry(radius = 0.58, segments = 32) {
    const geom = new THREE.BufferGeometry();
    const positions = [];
    const normals = [];
    const indices = [];

    const thetaSteps = segments * 2;
    const phiSteps = segments * 4;

    const grid = [];
    for (let i = 0; i <= thetaSteps; i++) {
      const row = [];
      const theta = (i / thetaSteps) * Math.PI;
      const sinTheta = Math.sin(theta);
      const cosTheta = Math.cos(theta);

      for (let j = 0; j <= phiSteps; j++) {
        const phi = (j / phiSteps) * Math.PI * 2;
        const sinPhi = Math.sin(phi);
        const cosPhi = Math.cos(phi);

        const x = radius * sinTheta * sinPhi;
        const y = radius * cosTheta;
        const z = radius * sinTheta * cosPhi;

        const norm = new THREE.Vector3(x, y, z).normalize();
        positions.push(x, y, z);
        normals.push(norm.x, norm.y, norm.z);
        row.push(positions.length / 3 - 1);
      }
      grid.push(row);
    }

    for (let i = 0; i < thetaSteps; i++) {
      const uMid = (i + 0.5) / thetaSteps;
      const thetaMid = uMid * Math.PI;
      const isYNeg = thetaMid > Math.PI * 0.5;

      for (let j = 0; j < phiSteps; j++) {
        const vMid = (j + 0.5) / phiSteps;
        const phiMid = vMid * Math.PI * 2;
        const isPhiInOctant = (phiMid >= Math.PI && phiMid <= Math.PI * 1.5);

        if (isYNeg && isPhiInOctant) continue;

        const a = grid[i][j];
        const b = grid[i + 1][j];
        const c = grid[i + 1][j + 1];
        const d = grid[i][j + 1];
        indices.push(a, b, d);
        indices.push(b, c, d);
      }
    }

    const cX = positions.length / 3;
    positions.push(0, 0, 0); normals.push(-1, 0, 0);
    const ringX = [];
    for (let j = 0; j <= segments; j++) {
      const ang = Math.PI + (j / segments) * Math.PI * 0.5;
      positions.push(0, radius * Math.cos(ang), radius * Math.sin(ang));
      normals.push(-1, 0, 0);
      ringX.push(positions.length / 3 - 1);
    }
    for (let j = 0; j < segments; j++) indices.push(cX, ringX[j], ringX[j + 1]);

    const cY = positions.length / 3;
    positions.push(0, 0, 0); normals.push(0, -1, 0);
    const ringY = [];
    for (let j = 0; j <= segments; j++) {
      const ang = Math.PI + (j / segments) * Math.PI * 0.5;
      positions.push(radius * Math.sin(ang), 0, radius * Math.cos(ang));
      normals.push(0, -1, 0);
      ringY.push(positions.length / 3 - 1);
    }
    for (let j = 0; j < segments; j++) indices.push(cY, ringY[j + 1], ringY[j]);

    const cZ = positions.length / 3;
    positions.push(0, 0, 0); normals.push(0, 0, -1);
    const ringZ = [];
    for (let j = 0; j <= segments; j++) {
      const ang = Math.PI + (j / segments) * Math.PI * 0.5;
      positions.push(radius * Math.sin(ang), radius * Math.cos(ang), 0);
      normals.push(0, 0, -1);
      ringZ.push(positions.length / 3 - 1);
    }
    for (let j = 0; j < segments; j++) indices.push(cZ, ringZ[j], ringZ[j + 1]);

    geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geom.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
    geom.setIndex(indices);
    return geom;
  }

  static createClippingPlanes(origin = new THREE.Vector3(0, 0, 0)) {
    return [
      new THREE.Plane(new THREE.Vector3(1, 0, 0), -origin.x),
      new THREE.Plane(new THREE.Vector3(0, 1, 0), -origin.y),
      new THREE.Plane(new THREE.Vector3(0, 0, 1), -origin.z)
    ];
  }
}
