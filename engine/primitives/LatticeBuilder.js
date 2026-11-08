import * as THREE from '../../assets/vendor/three.module.js';

export class LatticeBuilder {
  static buildDiamondCubic(scene, params = {}) {
    const {
      latticeConstant = 10.0,
      atomRadius = 0.56,
      cornerColor = 0xd8e2ec,
      faceColor = 0x00f0ff,
      interiorColor = 0xffd000,
      bondColor = 0x00f0ff,
      bondRadius = 0.12,
      showBonds = true,
      showWireframe = true,
      position = new THREE.Vector3(0, 0, 0)
    } = params;

    const group = new THREE.Group();
    group.position.copy(position);

    const L = latticeConstant;
    const halfL = L * 0.5;

    if (showWireframe) {
      const boxEdges = new THREE.EdgesGeometry(new THREE.BoxGeometry(L, L, L));
      const boxLineMat = new THREE.LineBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.45 });
      group.add(new THREE.LineSegments(boxEdges, boxLineMat));
    }

    const sphereGeo = new THREE.SphereGeometry(atomRadius, 32, 32);

    const cornerMat = new THREE.MeshPhysicalMaterial({
      color: cornerColor,
      emissive: 0x1e293b,
      emissiveIntensity: 0.4,
      metalness: 0.2,
      roughness: 0.08,
      clearcoat: 1.0
    });

    const faceMat = new THREE.MeshPhysicalMaterial({
      color: faceColor,
      emissive: faceColor,
      emissiveIntensity: 2.0,
      metalness: 0.1,
      roughness: 0.08,
      clearcoat: 1.0
    });

    const interiorMat = new THREE.MeshPhysicalMaterial({
      color: interiorColor,
      emissive: 0xff6b00,
      emissiveIntensity: 2.5,
      metalness: 0.1,
      roughness: 0.08,
      clearcoat: 1.0
    });

    const corners = [
      new THREE.Vector3(-halfL, -halfL, -halfL), new THREE.Vector3( halfL, -halfL, -halfL),
      new THREE.Vector3(-halfL,  halfL, -halfL), new THREE.Vector3( halfL,  halfL, -halfL),
      new THREE.Vector3(-halfL, -halfL,  halfL), new THREE.Vector3( halfL, -halfL,  halfL),
      new THREE.Vector3(-halfL,  halfL,  halfL), new THREE.Vector3( halfL,  halfL,  halfL)
    ];

    const faces = [
      new THREE.Vector3(0, 0, -halfL), new THREE.Vector3(0, 0,  halfL),
      new THREE.Vector3(0, -halfL, 0), new THREE.Vector3(0,  halfL, 0),
      new THREE.Vector3(-halfL, 0, 0), new THREE.Vector3( halfL, 0, 0)
    ];

    const interiors = [
      new THREE.Vector3(-halfL + 0.25 * L, -halfL + 0.25 * L, -halfL + 0.25 * L),
      new THREE.Vector3(-halfL + 0.75 * L, -halfL + 0.75 * L, -halfL + 0.25 * L),
      new THREE.Vector3(-halfL + 0.75 * L, -halfL + 0.25 * L, -halfL + 0.75 * L),
      new THREE.Vector3(-halfL + 0.25 * L, -halfL + 0.75 * L, -halfL + 0.75 * L)
    ];

    corners.forEach(p => {
      const m = new THREE.Mesh(sphereGeo, cornerMat);
      m.position.copy(p);
      group.add(m);
    });

    faces.forEach(p => {
      const m = new THREE.Mesh(sphereGeo, faceMat);
      m.position.copy(p);
      group.add(m);
    });

    interiors.forEach(p => {
      const m = new THREE.Mesh(sphereGeo, interiorMat);
      m.position.copy(p);
      group.add(m);
    });

    if (showBonds) {
      const bondMat = new THREE.MeshPhysicalMaterial({
        color: bondColor,
        emissive: bondColor,
        emissiveIntensity: 2.4,
        roughness: 0.1,
        clearcoat: 1.0,
        transparent: true,
        opacity: 0.95
      });

      interiors.forEach(intPos => {
        [...corners, ...faces].forEach(otherPos => {
          const d = intPos.distanceTo(otherPos);
          if (d > 0.1 && d <= 0.44 * L) {
            const cyl = new THREE.Mesh(new THREE.CylinderGeometry(bondRadius, bondRadius, d, 16), bondMat);
            cyl.position.copy(intPos.clone().add(otherPos).multiplyScalar(0.5));
            cyl.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), otherPos.clone().sub(intPos).normalize());
            group.add(cyl);
          }
        });
      });
    }

    if (scene) scene.add(group);
    return group;
  }

  static buildFCC(scene, params = {}) {
    const {
      latticeConstant = 10.0,
      atomRadius = 0.65,
      cornerColor = 0xd8e2ec,
      faceColor = 0x00f0ff,
      position = new THREE.Vector3(0, 0, 0)
    } = params;

    const group = new THREE.Group();
    group.position.copy(position);

    const L = latticeConstant;
    const halfL = L * 0.5;

    const boxEdges = new THREE.EdgesGeometry(new THREE.BoxGeometry(L, L, L));
    group.add(new THREE.LineSegments(boxEdges, new THREE.LineBasicMaterial({ color: 0x38bdf8, opacity: 0.4, transparent: true })));

    const sphereGeo = new THREE.SphereGeometry(atomRadius, 32, 32);
    const cornerMat = new THREE.MeshPhysicalMaterial({ color: cornerColor, roughness: 0.1, clearcoat: 1.0 });
    const faceMat = new THREE.MeshPhysicalMaterial({ color: faceColor, emissive: faceColor, emissiveIntensity: 1.8, clearcoat: 1.0 });

    for (let x of [-halfL, halfL]) {
      for (let y of [-halfL, halfL]) {
        for (let z of [-halfL, halfL]) {
          const m = new THREE.Mesh(sphereGeo, cornerMat);
          m.position.set(x, y, z);
          group.add(m);
        }
      }
    }

    const faceCenters = [
      new THREE.Vector3(0, 0, -halfL), new THREE.Vector3(0, 0,  halfL),
      new THREE.Vector3(0, -halfL, 0), new THREE.Vector3(0,  halfL, 0),
      new THREE.Vector3(-halfL, 0, 0), new THREE.Vector3( halfL, 0, 0)
    ];

    faceCenters.forEach(p => {
      const m = new THREE.Mesh(sphereGeo, faceMat);
      m.position.copy(p);
      group.add(m);
    });

    if (scene) scene.add(group);
    return group;
  }
}
