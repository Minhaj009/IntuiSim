/**
 * IntuiSim Modular 3D Asset Library - PotentialWellTerrain.js
 * 3D Kronig-Penney Periodic Potential Energy Landscape & Quantum Carrier Transport
 *
 * Adheres strictly to:
 * - Directive 18.2: The Physical Landscape Archetype (Continuous Deformable 3D Topography)
 * - Directive 22: Thermal Color Palette Shift (0 K Cryogenic Cobalt -> 300 K Amber Phonons)
 * - Course 1 Rule 1 & Course 4 Rule 1: Bloch Wavepacket with Phase Interference Fringes
 */

import * as THREE from '../vendor/three.module.js';

export class PotentialWellTerrain extends THREE.Group {
  /**
   * @param {Object} options
   * @param {number} [options.width=16.0] - X extent of terrain
   * @param {number} [options.depth=16.0] - Z extent of terrain
   * @param {number} [options.segmentsX=120] - X vertex resolution
   * @param {number} [options.segmentsZ=120] - Z vertex resolution
   * @param {number} [options.latticeConstant=3.2] - Periodic well spacing
   * @param {number} [options.initialTemperature=0.0] - Temperature in Kelvin (0 to 300 K)
   * @param {number} [options.wellDepth=1.8] - Attractive Coulomb well depth
   * @param {number} [options.barrierHeight=0.75] - Inter-atomic potential barrier peak
   */
  constructor(options = {}) {
    super();
    this.name = 'PotentialWellTerrain_KronigPenney';

    this.options = Object.assign({
      width: 16.0,
      depth: 16.0,
      segmentsX: 120,
      segmentsZ: 120,
      latticeConstant: 3.2,
      initialTemperature: 0.0,
      wellDepth: 1.8,
      barrierHeight: 0.75
    }, options);

    this.temperatureK = this.options.initialTemperature;
    this.wavepacketPos = new THREE.Vector2(0, 0);
    this.wavepacketActive = true;
    this._disposables = [];

    this._initMaterials();
    this._buildHeightfield();
    this._buildBlochWavepacket();
    this._buildLatticeAtomMarkers();

    this.setTemperature(this.temperatureK);
  }

  _initMaterials() {
    // Luxury Topographic Surface Material (Directive 3)
    // Deep obsidian wells transitioning to glowing cyan slopes and amber barrier crests
    this.terrainMaterial = new THREE.MeshPhysicalMaterial({
      roughness: 0.25,
      metalness: 0.2,
      clearcoat: 1.0,
      clearcoatRoughness: 0.06,
      vertexColors: true,
      side: THREE.DoubleSide
    });
    this._disposables.push(this.terrainMaterial);

    // Coordinate Isolines / Wireframe Overlay
    this.wireOverlayMat = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.18,
      blending: THREE.AdditiveBlending
    });
    this._disposables.push(this.wireOverlayMat);

    // Bloch Wavepacket Luminous Shell Material (Course 1 Rule 1)
    this.wavepacketMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xffb703,
      emissive: 0xd97706,
      emissiveIntensity: 2.2,
      roughness: 0.15,
      clearcoat: 1.0,
      transmission: 0.45,
      transparent: true,
      opacity: 0.85
    });
    this._disposables.push(this.wavepacketMaterial);

    // Interference Fringe Stripe Material
    this.fringeMaterial = new THREE.LineBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending
    });
    this._disposables.push(this.fringeMaterial);

    // Lattice Cation Markers (Deep in potential well cores)
    this.atomMarkerMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x0284c7,
      emissive: 0x00f0ff,
      emissiveIntensity: 1.2,
      roughness: 0.1,
      clearcoat: 1.0
    });
    this._disposables.push(this.atomMarkerMaterial);
  }

  _buildHeightfield() {
    this.terrainGroup = new THREE.Group();

    const w = this.options.width;
    const d = this.options.depth;
    const segX = this.options.segmentsX;
    const segZ = this.options.segmentsZ;

    this.geometry = new THREE.PlaneGeometry(w, d, segX, segZ);
    this.geometry.rotateX(-Math.PI / 2); // Lay horizontal on XZ plane
    this._disposables.push(this.geometry);

    // Cache unperturbed static potential heights V0(x, z)
    const posAttr = this.geometry.attributes.position;
    const count = posAttr.count;
    this.staticHeights = new Float32Array(count);
    this.colors = new Float32Array(count * 3);

    const a = this.options.latticeConstant;
    const V_well = this.options.wellDepth;
    const V_barrier = this.options.barrierHeight;

    // Lattice well centers
    const wellCenters = [];
    for (let x = -6.4; x <= 6.4; x += a) {
      for (let z = -6.4; z <= 6.4; z += a) {
        wellCenters.push(new THREE.Vector2(x, z));
      }
    }
    this.wellCenters = wellCenters;

    const colWell = new THREE.Color(0x0a1628);    // Deep obsidian/cobalt well
    const colSlope = new THREE.Color(0x10b981);   // Resonant emerald slope
    const colBarrier = new THREE.Color(0xf59e0b); // Potential barrier peak

    for (let i = 0; i < count; i++) {
      const x = posAttr.getX(i);
      const z = posAttr.getZ(i);

      // 1. Sum of attractive Coulomb/atomic wells
      let wellSum = 0;
      for (let j = 0; j < wellCenters.length; j++) {
        const dx = x - wellCenters[j].x;
        const dz = z - wellCenters[j].y;
        const distSq = dx * dx + dz * dz;
        wellSum += 1.0 / Math.sqrt(distSq + 0.38);
      }

      // 2. Periodic Kronig-Penney barrier modulation
      const barrier = V_barrier * (Math.cos((2 * Math.PI * x) / a) * Math.cos((2 * Math.PI * z) / a));

      // Potential energy height V(x,z)
      const y = -V_well * (wellSum * 0.35) + barrier;
      this.staticHeights[i] = y;
      posAttr.setY(i, y);

      // Vertex color mapping based on potential energy
      const normY = THREE.MathUtils.clamp((y + 2.5) / 3.2, 0.0, 1.0);
      let vColor = new THREE.Color();
      if (normY < 0.45) {
        vColor.copy(colWell).lerp(colSlope, normY / 0.45);
      } else {
        vColor.copy(colSlope).lerp(colBarrier, (normY - 0.45) / 0.55);
      }

      this.colors[i * 3] = vColor.r;
      this.colors[i * 3 + 1] = vColor.g;
      this.colors[i * 3 + 2] = vColor.b;
    }

    this.geometry.setAttribute('color', new THREE.BufferAttribute(this.colors, 3));
    this.geometry.computeVertexNormals();

    this.terrainMesh = new THREE.Mesh(this.geometry, this.terrainMaterial);
    this.terrainGroup.add(this.terrainMesh);

    // Subtle wireframe grid
    const wireGeo = new THREE.WireframeGeometry(this.geometry);
    this._disposables.push(wireGeo);
    this.wireMesh = new THREE.LineSegments(wireGeo, this.wireOverlayMat);
    this.terrainGroup.add(this.wireMesh);

    this.add(this.terrainGroup);
  }

  _buildBlochWavepacket() {
    this.wavepacketGroup = new THREE.Group();
    this.wavepacketGroup.name = 'blochWavepacket';

    // Localized Gaussian Envelope Envelope (Course 1 Rule 1)
    const packetGeo = new THREE.SphereGeometry(0.75, 24, 24);
    packetGeo.scale(1.2, 0.65, 1.2);
    this._disposables.push(packetGeo);

    this.packetMesh = new THREE.Mesh(packetGeo, this.wavepacketMaterial);
    this.wavepacketGroup.add(this.packetMesh);

    // Dynamic Phase Interference Rings (ψ_k(r,t) fringes)
    this.fringeRings = [];
    for (let r = 0.25; r <= 1.0; r += 0.25) {
      const ringGeo = new THREE.RingGeometry(r - 0.02, r + 0.02, 32);
      ringGeo.rotateX(-Math.PI / 2);
      this._disposables.push(ringGeo);

      const ringMesh = new THREE.Mesh(ringGeo, this.fringeMaterial);
      this.wavepacketGroup.add(ringMesh);
      this.fringeRings.push(ringMesh);
    }

    this.add(this.wavepacketGroup);
  }

  _buildLatticeAtomMarkers() {
    this.markersGroup = new THREE.Group();
    const markerGeo = new THREE.SphereGeometry(0.18, 16, 16);
    this._disposables.push(markerGeo);

    this.wellCenters.forEach(wc => {
      const mesh = new THREE.Mesh(markerGeo, this.atomMarkerMaterial);
      mesh.position.set(wc.x, -1.9, wc.y);
      this.markersGroup.add(mesh);
    });

    this.add(this.markersGroup);
  }

  /**
   * Evaluates the potential surface height at any (x, z)
   */
  getSurfaceElevation(x, z) {
    const a = this.options.latticeConstant;
    let wellSum = 0;
    for (let j = 0; j < this.wellCenters.length; j++) {
      const dx = x - this.wellCenters[j].x;
      const dz = z - this.wellCenters[j].y;
      wellSum += 1.0 / Math.sqrt(dx * dx + dz * dz + 0.38);
    }
    const barrier = this.options.barrierHeight * (Math.cos((2 * Math.PI * x) / a) * Math.cos((2 * Math.PI * z) / a));
    return -this.options.wellDepth * (wellSum * 0.35) + barrier;
  }

  /**
   * Continuous animation update (Directive 6)
   */
  update(t, delta = 0.016) {
    const posAttr = this.geometry.attributes.position;
    const count = posAttr.count;

    // 1. Thermal Acoustic Phonon Vibration Waves (0 K -> 300 K)
    const phononAmp = (this.temperatureK / 300.0) * 0.24;

    if (phononAmp > 0.001) {
      for (let i = 0; i < count; i++) {
        const x = posAttr.getX(i);
        const z = posAttr.getZ(i);
        const staticY = this.staticHeights[i];

        // Superposition of 3 non-collinear acoustic phonon modes
        const wave1 = Math.sin(1.8 * x + 2.2 * z - t * 4.5);
        const wave2 = Math.cos(2.4 * x - 1.6 * z + t * 3.8);
        const wave3 = Math.sin(0.9 * x - 0.7 * z - t * 2.1);
        const dy = phononAmp * (wave1 * 0.45 + wave2 * 0.35 + wave3 * 0.20);

        posAttr.setY(i, staticY + dy);
      }
      posAttr.needsUpdate = true;
      this.geometry.computeVertexNormals();
    }

    // 2. Bloch Wavepacket Glide & Phase Ripple
    if (this.wavepacketActive) {
      const wx = this.wavepacketPos.x;
      const wz = this.wavepacketPos.y;
      const surfaceY = this.getSurfaceElevation(wx, wz);

      // Packet rides smoothly across potential contours
      this.wavepacketGroup.position.set(wx, surfaceY + 0.55, wz);

      // Wavepacket quantum phase pulse: cos(k·r - ωt)
      const phasePulse = Math.sin(t * 6.0) * 0.35 + 2.2;
      this.wavepacketMaterial.emissiveIntensity = phasePulse;

      // Expand phase interference fringes outward
      this.fringeRings.forEach((ring, idx) => {
        const phaseShift = (t * 2.0 + idx * 0.3) % 1.0;
        ring.scale.setScalar(0.7 + phaseShift * 0.8);
      });
    }
  }

  /**
   * Sets lattice temperature in Kelvin (Directive 22 thermal transition)
   * @param {number} tempK - 0.0 K (cryogenic freeze) to 300.0 K (room temperature agitation)
   */
  setTemperature(tempK) {
    this.temperatureK = THREE.MathUtils.clamp(tempK, 0.0, 300.0);

    // Warm palette shift as temperature increases
    const thermalRatio = this.temperatureK / 300.0;
    if (this.wireOverlayMat) {
      this.wireOverlayMat.color.setRGB(
        0.22 + thermalRatio * 0.7,
        0.74 - thermalRatio * 0.3,
        0.97 - thermalRatio * 0.6
      );
    }
  }

  /**
   * Sets 2D (X, Z) coordinate of the Bloch wavepacket
   */
  setWavepacketPosition(x, z) {
    this.wavepacketPos.set(x, z);
  }

  /**
   * Toggles wavepacket visibility
   */
  setWavepacketActive(bool) {
    this.wavepacketActive = !!bool;
    this.wavepacketGroup.visible = this.wavepacketActive;
  }

  getAnnotations() {
    this.updateMatrixWorld(true);

    const wpWorld = new THREE.Vector3();
    this.wavepacketGroup.getWorldPosition(wpWorld);

    return {
      wavepacket: {
        id: 'bloch-wavepacket',
        label: 'BLOCH WAVEPACKET ψ_k(r,t)',
        worldPosition: wpWorld,
        caption: 'Quantum electron delocalized across periodic potential wells'
      },
      potentialWell: {
        id: 'attractive-well',
        label: 'COULOMB POTENTIAL WELL V(r)',
        worldPosition: new THREE.Vector3(0, -1.8, 0),
        caption: 'Deep attractive potential binding electrons near atomic cores'
      },
      barrierPeak: {
        id: 'potential-barrier',
        label: 'PERIODIC BARRIER PEAK',
        worldPosition: new THREE.Vector3(1.6, 0.7, 1.6),
        caption: 'Potential barrier governing quantum tunneling and bandgap formation'
      }
    };
  }

  dispose() {
    this._disposables.forEach(item => {
      if (item && typeof item.dispose === 'function') {
        item.dispose();
      }
    });
    this._disposables = [];
    this.wellCenters = [];
    this.clear();
  }
}
