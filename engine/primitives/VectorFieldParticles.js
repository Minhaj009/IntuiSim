import * as THREE from '../../assets/vendor/three.module.js';

export class VectorFieldParticles {
  constructor(fieldFn, count = 1200, bounds = { min: [-10, -10, -10], max: [10, 10, 10] }) {
    this.fieldFn = fieldFn || ((x, y, z) => new THREE.Vector3(-y, x, 0.2).normalize());
    this.count = count;
    this.bounds = bounds;

    const geo = new THREE.SphereGeometry(0.08, 8, 8);
    const mat = new THREE.MeshPhysicalMaterial({
      color: 0x00f0ff,
      emissive: 0x00f0ff,
      emissiveIntensity: 3.0,
      clearcoat: 1.0
    });

    this.mesh = new THREE.InstancedMesh(geo, mat, count);
    this.positions = [];
    this.speeds = [];

    const dummy = new THREE.Object3D();
    for (let i = 0; i < count; i++) {
      const p = new THREE.Vector3(
        THREE.MathUtils.randFloat(bounds.min[0], bounds.max[0]),
        THREE.MathUtils.randFloat(bounds.min[1], bounds.max[1]),
        THREE.MathUtils.randFloat(bounds.min[2], bounds.max[2])
      );
      this.positions.push(p);
      this.speeds.push(THREE.MathUtils.randFloat(2.5, 5.0));

      dummy.position.copy(p);
      dummy.updateMatrix();
      this.mesh.setMatrixAt(i, dummy.matrix);
    }
    this.mesh.instanceMatrix.needsUpdate = true;
  }

  step(dt = 0.016) {
    const dummy = new THREE.Object3D();
    for (let i = 0; i < this.count; i++) {
      const p = this.positions[i];
      const vel = this.fieldFn(p.x, p.y, p.z).multiplyScalar(this.speeds[i] * dt);
      p.add(vel);

      for (let axis = 0; axis < 3; axis++) {
        const coord = axis === 0 ? 'x' : axis === 1 ? 'y' : 'z';
        if (p[coord] < this.bounds.min[axis]) p[coord] = this.bounds.max[axis];
        if (p[coord] > this.bounds.max[axis]) p[coord] = this.bounds.min[axis];
      }

      dummy.position.copy(p);
      dummy.updateMatrix();
      this.mesh.setMatrixAt(i, dummy.matrix);
    }
    this.mesh.instanceMatrix.needsUpdate = true;
  }
}
