import * as THREE from '../../assets/vendor/three.module.js';

export class TopographicSurface3D {
  constructor(params = {}) {
    this.width = params.width || 24;
    this.height = params.height || 24;
    this.segmentsX = params.segmentsX || 80;
    this.segmentsY = params.segmentsY || 80;
    this.potentialFn = params.potentialFn || ((x, y) => 2.5 * Math.sin(0.3 * x) * Math.cos(0.3 * y));
    this.group = new THREE.Group();
    this.particles = [];

    this.mesh = this.generateMesh();
    this.group.add(this.mesh);
  }

  generateMesh() {
    const geo = new THREE.PlaneGeometry(this.width, this.height, this.segmentsX, this.segmentsY);
    geo.rotateX(-Math.PI * 0.5);

    const pos = geo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      pos.setY(i, this.potentialFn(x, z));
    }
    geo.computeVertexNormals();

    const mat = new THREE.MeshPhysicalMaterial({
      color: 0x0a1628,
      emissive: 0x00f0ff,
      emissiveIntensity: 0.35,
      roughness: 0.15,
      metalness: 0.2,
      clearcoat: 1.0,
      wireframe: false,
      side: THREE.DoubleSide
    });

    return new THREE.Mesh(geo, mat);
  }

  generateContourLines(numLevels = 10) {
    const wireMat = new THREE.LineBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.4 });
    const wireGeo = new THREE.WireframeGeometry(this.mesh.geometry);
    const wire = new THREE.LineSegments(wireGeo, wireMat);
    this.group.add(wire);
    return wire;
  }

  spawnTestParticle(x, z) {
    const geo = new THREE.SphereGeometry(0.2, 16, 16);
    const mat = new THREE.MeshPhysicalMaterial({ color: 0xffd000, emissive: 0xff6b00, emissiveIntensity: 3.0 });
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, this.potentialFn(x, z) + 0.25, z);
    m.userData.vx = 0;
    m.userData.vz = 0;
    this.group.add(m);
    this.particles.push(m);
    return m;
  }

  stepParticles(dt = 0.016) {
    const eps = 0.05;
    const damping = 0.96;
    const gravity = 9.8;

    this.particles.forEach(p => {
      const x = p.position.x;
      const z = p.position.z;

      const gradX = (this.potentialFn(x + eps, z) - this.potentialFn(x - eps, z)) / (2 * eps);
      const gradZ = (this.potentialFn(x, z + eps) - this.potentialFn(x, z - eps)) / (2 * eps);

      p.userData.vx = (p.userData.vx - gradX * gravity * dt) * damping;
      p.userData.vz = (p.userData.vz - gradZ * gravity * dt) * damping;

      p.position.x += p.userData.vx * dt;
      p.position.z += p.userData.vz * dt;
      p.position.y = this.potentialFn(p.position.x, p.position.z) + 0.25;
    });
  }

  updatePotential(newFn) {
    this.potentialFn = newFn;
    const pos = this.mesh.geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      pos.setY(i, this.potentialFn(x, z));
    }
    pos.needsUpdate = true;
    this.mesh.geometry.computeVertexNormals();
  }
}
