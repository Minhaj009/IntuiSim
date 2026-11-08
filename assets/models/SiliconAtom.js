/**
 * IntuiSim Modular 3D Asset Library - SiliconAtom.js
 * Isolated Silicon Atom (Z=14) with Neon-like core [Ne] and valence M-shell [3s² 3p²]
 *
 * Adheres strictly to:
 * - Directive 3: Ultra-Luxury Physical Materials (clearcoat: 1.0, clearcoatRoughness: 0.04)
 * - Directive 14 & 18.1: Dynamic Geometric Disassembly & Attentive Attenuation
 * - Rule D1: Exploded Anatomical Dissection along Axial Rails
 * - Rule R1: Manifold Watertight Primitives & Bounded Slicing
 */

import * as THREE from '../vendor/three.module.js';

export class SiliconAtom extends THREE.Group {
  /**
   * @param {Object} options
   * @param {number} [options.radius=1.5] - Visual base scale radius
   * @param {number} [options.coreRadius=0.7] - Neon core bounding radius
   * @param {number} [options.valenceRadius=2.4] - Outer M-shell valence radius
   * @param {boolean} [options.showRadialNodes=false] - Initial visibility of 3s/3p radial nodes
   * @param {boolean} [options.laserPlaneActive=false] - Initial state of laser-slice plane
   * @param {string} [options.materialStyle='luxury'] - 'luxury' | 'wireframe' | 'xray'
   */
  constructor(options = {}) {
    super();
    this.name = 'SiliconAtom_Z14';

    this.options = Object.assign({
      radius: 1.5,
      coreRadius: 0.7,
      valenceRadius: 2.4,
      showRadialNodes: false,
      laserPlaneActive: false,
      materialStyle: 'luxury'
    }, options);

    this.disassemblyProgress = 0.0;
    this.laserPlaneY = 0.0;
    this._electronOrbits = [];
    this._disposables = [];

    this._initMaterials();
    this._buildNucleus();
    this._buildCoreShells();
    this._buildValenceShell();
    this._buildRadialNodes();
    this._buildLaserSlicePlane();

    this.setRadialNodesVisible(this.options.showRadialNodes);
    this.setLaserPlane(0.0, this.options.laserPlaneActive);
  }

  _initMaterials() {
    const isWire = this.options.materialStyle === 'wireframe';
    const isXRay = this.options.materialStyle === 'xray';

    // Nucleus: Incandescent Gold / Amber +14q Core (Directive 3 & 22)
    this.nucleusMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xffb703,
      emissive: 0xd97706,
      emissiveIntensity: 2.2,
      roughness: 0.15,
      metalness: 0.1,
      clearcoat: 1.0,
      clearcoatRoughness: 0.04,
      wireframe: isWire
    });
    this._disposables.push(this.nucleusMaterial);

    // Core Electron Material: Cool Diamond Blue Specular
    this.coreElectronMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x38bdf8,
      emissive: 0x0284c7,
      emissiveIntensity: 1.8,
      roughness: 0.12,
      clearcoat: 1.0,
      clearcoatRoughness: 0.05,
      wireframe: isWire
    });
    this._disposables.push(this.coreElectronMaterial);

    // Valence Electron Material: Radiant Neon Cyan (High Saliency - Directive 15)
    this.valenceElectronMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x00f0ff,
      emissive: 0x00f0ff,
      emissiveIntensity: 2.6,
      roughness: 0.08,
      clearcoat: 1.0,
      clearcoatRoughness: 0.02,
      wireframe: isWire
    });
    this._disposables.push(this.valenceElectronMaterial);

    // Orbit Ring Materials: Hairline Frosted Glass Trails
    this.orbitRingMaterial = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: isXRay ? 0.6 : 0.35,
      blending: THREE.AdditiveBlending
    });
    this._disposables.push(this.orbitRingMaterial);

    this.valenceRingMaterial = new THREE.LineBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: isXRay ? 0.75 : 0.45,
      blending: THREE.AdditiveBlending
    });
    this._disposables.push(this.valenceRingMaterial);

    // Radial Nodal Plane Material: Translucent Emerald Glass (Directive 22)
    this.nodalMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x10b981,
      emissive: 0x059669,
      emissiveIntensity: 0.85,
      transmission: 0.82,
      opacity: 0.38,
      transparent: true,
      roughness: 0.18,
      ior: 1.45,
      thickness: 0.8,
      side: THREE.DoubleSide,
      depthWrite: false
    });
    this._disposables.push(this.nodalMaterial);

    // Laser Slice Material: High-contrast Cyan / Indigo Optical Sheet
    this.laserSheetMaterial = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.22,
      side: THREE.DoubleSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });
    this.laserRimMaterial = new THREE.LineBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.95,
      blending: THREE.AdditiveBlending
    });
    this._disposables.push(this.laserSheetMaterial, this.laserRimMaterial);
  }

  _buildNucleus() {
    this.nucleusGroup = new THREE.Group();
    this.nucleusGroup.name = 'nucleusGroup';

    // Central positive core sphere (+14 charge)
    const geo = new THREE.SphereGeometry(this.options.radius * 0.28, 36, 36);
    this._disposables.push(geo);
    this.nucleusMesh = new THREE.Mesh(geo, this.nucleusMaterial);
    this.nucleusGroup.add(this.nucleusMesh);

    // Optical Corona Glow Halo
    const haloGeo = new THREE.SphereGeometry(this.options.radius * 0.34, 24, 24);
    const haloMat = new THREE.MeshBasicMaterial({
      color: 0xffb703,
      transparent: true,
      opacity: 0.18,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending
    });
    this._disposables.push(haloGeo, haloMat);
    this.nucleusHalo = new THREE.Mesh(haloGeo, haloMat);
    this.nucleusGroup.add(this.nucleusHalo);

    this.add(this.nucleusGroup);
  }

  _buildCoreShells() {
    this.coreShellsGroup = new THREE.Group();
    this.coreShellsGroup.name = 'coreShellsGroup';

    const rCore = this.options.coreRadius;
    const eRadius = 0.055;

    // 1s Shell (n=1, 2 electrons)
    const r1s = rCore * 0.65;
    this._createOrbitRing(this.coreShellsGroup, r1s, this.orbitRingMaterial, new THREE.Euler(0, 0, 0));
    this._createElectron(this.coreShellsGroup, r1s, 0.0, 1.8, eRadius, this.coreElectronMaterial);
    this._createElectron(this.coreShellsGroup, r1s, Math.PI, 1.8, eRadius, this.coreElectronMaterial);

    // 2s Shell (n=2, 2 electrons, inclined orbit)
    const r2s = rCore * 1.15;
    const tilt2s = new THREE.Euler(THREE.MathUtils.degToRad(35), 0, THREE.MathUtils.degToRad(20));
    this._createOrbitRing(this.coreShellsGroup, r2s, this.orbitRingMaterial, tilt2s);
    this._createElectron(this.coreShellsGroup, r2s, 0.4, 1.4, eRadius, this.coreElectronMaterial, tilt2s);
    this._createElectron(this.coreShellsGroup, r2s, 0.4 + Math.PI, 1.4, eRadius, this.coreElectronMaterial, tilt2s);

    // 2p Shell (n=2, 6 electrons across 3 orthogonal orbits)
    const r2p = rCore * 1.45;
    const pRotations = [
      new THREE.Euler(0, 0, 0),
      new THREE.Euler(Math.PI / 2, 0, 0),
      new THREE.Euler(0, 0, Math.PI / 2)
    ];

    pRotations.forEach((rot, idx) => {
      this._createOrbitRing(this.coreShellsGroup, r2p, this.orbitRingMaterial, rot);
      const speed = 1.1 + idx * 0.2;
      const phaseOffset = idx * (Math.PI / 3);
      this._createElectron(this.coreShellsGroup, r2p, phaseOffset, speed, eRadius, this.coreElectronMaterial, rot);
      this._createElectron(this.coreShellsGroup, r2p, phaseOffset + Math.PI, speed, eRadius, this.coreElectronMaterial, rot);
    });

    this.add(this.coreShellsGroup);
  }

  _buildValenceShell() {
    this.valenceGroup = new THREE.Group();
    this.valenceGroup.name = 'valenceGroup';

    const rVal = this.options.valenceRadius;
    const eRadius = 0.085; // Distinct, high-salience valence carriers (Directive 15)

    // Valence orbits arranged in tetrahedral planes
    const tilts = [
      new THREE.Euler(0.4, 0.2, 0.0),
      new THREE.Euler(-0.4, 0.8, 0.5),
      new THREE.Euler(0.7, -0.5, 0.3),
      new THREE.Euler(-0.6, -0.6, -0.4)
    ];

    tilts.forEach((tilt, idx) => {
      this._createOrbitRing(this.valenceGroup, rVal, this.valenceRingMaterial, tilt);
      const phase = (idx * Math.PI) / 2;
      const speed = 0.85;
      this._createElectron(this.valenceGroup, rVal, phase, speed, eRadius, this.valenceElectronMaterial, tilt, true);
    });

    this.add(this.valenceGroup);
  }

  _buildRadialNodes() {
    this.nodalPlanesGroup = new THREE.Group();
    this.nodalPlanesGroup.name = 'nodalPlanesGroup';

    // Silicon 3s has 2 radial nodes (n - l - 1 = 3 - 0 - 1 = 2)
    const node1Radius = this.options.coreRadius * 0.95;
    const node2Radius = this.options.valenceRadius * 0.72;

    const geo1 = new THREE.SphereGeometry(node1Radius, 32, 24);
    const geo2 = new THREE.SphereGeometry(node2Radius, 32, 24);
    this._disposables.push(geo1, geo2);

    this.nodeSphere1 = new THREE.Mesh(geo1, this.nodalMaterial);
    this.nodeSphere2 = new THREE.Mesh(geo2, this.nodalMaterial);
    this.nodalPlanesGroup.add(this.nodeSphere1);
    this.nodalPlanesGroup.add(this.nodeSphere2);

    // Silicon 3p dumbbell nodal plane passing through origin (xy-plane cut)
    const planeGeo = new THREE.RingGeometry(0.1, this.options.valenceRadius * 0.9, 32);
    this._disposables.push(planeGeo);
    this.angularNodalDisk = new THREE.Mesh(planeGeo, this.nodalMaterial);
    this.angularNodalDisk.rotation.x = Math.PI / 2;
    this.nodalPlanesGroup.add(this.angularNodalDisk);

    this.add(this.nodalPlanesGroup);
  }

  _buildLaserSlicePlane() {
    this.laserSlicePlane = new THREE.Group();
    this.laserSlicePlane.name = 'laserSlicePlane';

    const span = this.options.valenceRadius * 2.8;
    const planeGeo = new THREE.PlaneGeometry(span, span);
    const edgesGeo = new THREE.EdgesGeometry(planeGeo);
    this._disposables.push(planeGeo, edgesGeo);

    this.laserMesh = new THREE.Mesh(planeGeo, this.laserSheetMaterial);
    this.laserMesh.rotation.x = -Math.PI / 2;
    this.laserSlicePlane.add(this.laserMesh);

    this.laserEdges = new THREE.LineSegments(edgesGeo, this.laserRimMaterial);
    this.laserEdges.rotation.x = -Math.PI / 2;
    this.laserSlicePlane.add(this.laserEdges);

    this.add(this.laserSlicePlane);
  }

  _createOrbitRing(parentGroup, radius, material, rotationEuler) {
    const segments = 64;
    const points = [];
    for (let i = 0; i <= segments; i++) {
      const theta = (i / segments) * Math.PI * 2;
      points.push(new THREE.Vector3(Math.cos(theta) * radius, 0, Math.sin(theta) * radius));
    }
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    this._disposables.push(geo);

    const line = new THREE.Line(geo, material);
    line.rotation.copy(rotationEuler);
    parentGroup.add(line);
  }

  _createElectron(parentGroup, orbitRadius, initialPhase, angularSpeed, size, material, rotationEuler = new THREE.Euler(), isValence = false) {
    const geo = new THREE.SphereGeometry(size, 20, 20);
    this._disposables.push(geo);

    const mesh = new THREE.Mesh(geo, material);
    parentGroup.add(mesh);

    this._electronOrbits.push({
      mesh,
      orbitRadius,
      phase: initialPhase,
      speed: angularSpeed,
      rotationEuler,
      isValence
    });
  }

  /**
   * Continuous animation update (Directive 6 & Rule D1)
   */
  update(t, delta = 0.016) {
    // 1. Electron orbital movement
    this._electronOrbits.forEach(e => {
      e.phase += e.speed * delta;
      const x = Math.cos(e.phase) * e.orbitRadius;
      const z = Math.sin(e.phase) * e.orbitRadius;
      const pos = new THREE.Vector3(x, 0, z);
      pos.applyEuler(e.rotationEuler);
      e.mesh.position.copy(pos);
    });

    // 2. Nucleus breathing luminescence
    if (this.nucleusMaterial) {
      const pulse = Math.sin(t * 3.2) * 0.35 + 2.2;
      this.nucleusMaterial.emissiveIntensity = pulse;
    }

    // 3. Laser slice plane emissive shimmer
    if (this.laserSlicePlane.visible && this.laserSheetMaterial) {
      this.laserSheetMaterial.opacity = 0.22 + Math.sin(t * 5.0) * 0.06;
    }

    // 4. Nodal plane gentle quantum breathing
    if (this.nodalPlanesGroup.visible) {
      const nodePulse = 1.0 + Math.sin(t * 1.8) * 0.02;
      this.nodeSphere1.scale.setScalar(nodePulse);
      this.nodeSphere2.scale.setScalar(nodePulse);
    }
  }

  /**
   * Sets disassembly rail progression (0.0 = unified, 1.0 = fully decoupled along axial rails)
   * Disassembles Neon core along +X and Valence M-shell along -X (Rule D1 & Directive 18.1)
   */
  setDisassemblyRail(progress) {
    const p = THREE.MathUtils.clamp(progress, 0.0, 1.0);
    this.disassemblyProgress = p;

    // Smoothstep cubic easing
    const s = p * p * (3 - 2 * p);
    const railDistance = 3.6;

    // Neon core slides along +X
    this.coreShellsGroup.position.x = railDistance * s;

    // Valence shell slides along -X
    this.valenceGroup.position.x = -railDistance * s;

    // Nucleus elevates slightly along +Y for unobstructed inspection (Rule O1)
    this.nucleusGroup.position.y = 0.65 * s;
  }

  /**
   * Sets height and active visibility of laser cutting sweep plane
   */
  setLaserPlane(yOffset, active = true) {
    this.laserPlaneY = yOffset;
    this.laserSlicePlane.position.y = yOffset;
    this.laserSlicePlane.visible = !!active;
  }

  /**
   * Controls radial node shell visibility
   */
  setRadialNodesVisible(bool) {
    this.nodalPlanesGroup.visible = !!bool;
  }

  /**
   * World-space annotation coordinates and metadata for dynamic SVG leader lines (Directive 9 & 18.3)
   */
  getAnnotations() {
    this.updateMatrixWorld(true);

    const nucPos = new THREE.Vector3();
    this.nucleusMesh.getWorldPosition(nucPos);

    const corePos = new THREE.Vector3();
    this.coreShellsGroup.getWorldPosition(corePos);
    corePos.y += this.options.coreRadius * 0.7;

    const valPos = new THREE.Vector3();
    this.valenceGroup.getWorldPosition(valPos);
    valPos.y += this.options.valenceRadius * 0.6;

    const laserPos = new THREE.Vector3();
    this.laserSlicePlane.getWorldPosition(laserPos);

    return {
      nucleus: {
        id: 'silicon-nucleus',
        label: 'NUCLEUS (+14q)',
        category: 'core',
        worldPosition: nucPos,
        caption: 'Central positive charge holding 14 protons & 14 neutrons'
      },
      coreShells: {
        id: 'neon-core',
        label: 'NEON-LIKE CORE [Ne]',
        category: 'core-shell',
        worldPosition: corePos,
        caption: '10 inert, tightly bound core electrons: 1s² 2s² 2p⁶'
      },
      valenceShell: {
        id: 'valence-m-shell',
        label: 'VALENCE M-SHELL (n=3)',
        category: 'valence',
        worldPosition: valPos,
        caption: '4 reactive outer electrons (3s² 3p²) governing covalent bonding'
      },
      radialNodes: {
        id: 'radial-nodes-3s',
        label: '3s RADIAL NODES (n - l - 1 = 2)',
        category: 'quantum',
        worldPosition: nucPos.clone().add(new THREE.Vector3(0, this.options.coreRadius * 0.95, 0)),
        caption: 'Concentric zero-probability spherical shells where wavefunction ψ = 0'
      },
      laserSlice: {
        id: 'laser-cut-plane',
        label: 'LASER SLICE PLANE',
        category: 'instrument',
        worldPosition: laserPos,
        caption: 'Optical section exposing internal electron probability density'
      }
    };
  }

  /**
   * Strict WebGL GPU memory cleanup
   */
  dispose() {
    this._disposables.forEach(item => {
      if (item && typeof item.dispose === 'function') {
        item.dispose();
      }
    });
    this._disposables = [];
    this._electronOrbits = [];
    this.clear();
  }
}
