import * as THREE from '../../assets/vendor/three.module.js';

export class WavepacketField {
  constructor(params = {}) {
    this.xMin = params.xMin ?? -12;
    this.xMax = params.xMax ?? 12;
    this.numSamples = params.numSamples ?? 240;
    this.barrierX = params.barrierX ?? 0.0;
    this.barrierWidth = params.barrierWidth ?? 1.2;
    this.barrierHeight = params.barrierHeight ?? 4.0;
    this.packetEnergy = params.packetEnergy ?? 2.8;
    this.x0 = params.x0 ?? -7.0;
    this.sigma0 = params.sigma0 ?? 1.2;
    this.k0 = params.k0 ?? 3.5;

    this.group = new THREE.Group();
    this.mesh = this.createWaveMesh();
    this.barrierMesh = this.createBarrierMesh();
    this.group.add(this.mesh);
    this.group.add(this.barrierMesh);
  }

  createWaveMesh() {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(this.numSamples * 2 * 3);
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const mat = new THREE.MeshPhysicalMaterial({
      color: 0x00f0ff,
      emissive: 0x00f0ff,
      emissiveIntensity: 2.2,
      roughness: 0.1,
      metalness: 0.1,
      clearcoat: 1.0,
      side: THREE.DoubleSide
    });

    return new THREE.Mesh(geo, mat);
  }

  createBarrierMesh() {
    const geo = new THREE.BoxGeometry(this.barrierWidth, this.barrierHeight, 2.0);
    const mat = new THREE.MeshPhysicalMaterial({
      color: 0xffd000,
      emissive: 0xff6b00,
      emissiveIntensity: 2.0,
      transmission: 0.7,
      transparent: true,
      opacity: 0.65,
      roughness: 0.1
    });
    const m = new THREE.Mesh(geo, mat);
    m.position.set(this.barrierX, this.barrierHeight * 0.5, 0);
    return m;
  }

  computeTunnelingProbability() {
    const V0 = this.barrierHeight;
    const E = this.packetEnergy;
    const a = this.barrierWidth;
    if (E >= V0) return 1.0;
    const kappa = Math.sqrt(2.0 * (V0 - E));
    const denom = 1.0 + (V0 * V0 * Math.sinh(kappa * a) ** 2) / (4.0 * E * (V0 - E));
    return 1.0 / denom;
  }

  step(t) {
    const pos = this.mesh.geometry.attributes.position;
    const dx = (this.xMax - this.xMin) / (this.numSamples - 1);
    const vg = this.k0 * 0.8;
    const currentX0 = this.x0 + vg * t;

    let idx = 0;
    for (let i = 0; i < this.numSamples; i++) {
      const x = this.xMin + i * dx;
      const env = Math.exp(-((x - currentX0) ** 2) / (4.0 * this.sigma0 ** 2));
      const psiReal = env * Math.cos(this.k0 * x - 3.0 * t);
      const amp = psiReal * 2.5;

      pos.setXYZ(idx++, x, amp, -0.6);
      pos.setXYZ(idx++, x, amp,  0.6);
    }
    pos.needsUpdate = true;
    this.mesh.geometry.computeVertexNormals();
  }
}
