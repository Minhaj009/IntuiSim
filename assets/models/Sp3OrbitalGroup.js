/**
 * IntuiSim Modular 3D Asset Library - Sp3OrbitalGroup.js
 * Atomic Orbital Basis {|3s⟩, |3px⟩, |3py⟩, |3pz⟩} & sp³ Tetrahedral Hybridization
 *
 * Adheres strictly to:
 * - Rule R1: Watertight Solid Parametric Lathe Geometry (No hollow clipped spheres!)
 * - Directive 3: Ultra-Luxury Physical Transmission Materials (transmission: 0.15, clearcoat: 1.0)
 * - Directive 16 & 23.2: Congruence of Motion & 109.47° Tetrahedral Scaffolding
 * - Directive 24.5: Calibrated Laser Caliper Dimensioning Arc
 */

import * as THREE from '../vendor/three.module.js';

export class Sp3OrbitalGroup extends THREE.Group {
  /**
   * @param {Object} options
   * @param {number} [options.scale=1.0] - General scaling factor
   * @param {number} [options.lobeLength=2.8] - Major lobe peak reach
   * @param {number} [options.hybridization=0.0] - 0.0 = pure unhybridized basis, 1.0 = pure sp³
   * @param {boolean} [options.caliperActive=false] - 109.47° caliper measurement arc
   * @param {number} [options.lcaoDistance=5.0] - LCAO inter-atomic distance (5.0 = isolated, 2.35 = bonded)
   */
  constructor(options = {}) {
    super();
    this.name = 'Sp3OrbitalGroup';

    this.options = Object.assign({
      scale: 1.0,
      lobeLength: 2.8,
      hybridization: 0.0,
      caliperActive: false,
      lcaoDistance: 5.0
    }, options);

    this.hybridizationFactor = this.options.hybridization;
    this.caliperActive = this.options.caliperActive;
    this.lcaoDistance = this.options.lcaoDistance;
    this._disposables = [];

    this._initMaterials();
    this._buildBasisPedestals();
    this._buildSp3HybridLobes();
    this._buildCaliperArc();
    this._buildLCAOMolecularState();

    this.setHybridization(this.hybridizationFactor);
    this.setCaliperActive(this.caliperActive);
    this.setLCAOOverlap(this.lcaoDistance);
  }

  _initMaterials() {
    // Rule R1: Luxury Physical Materials with Glass Depth
    // Emerald Green (+ phase) Major Hybrid / Bonding Lobe
    this.positivePhaseMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x10b981,
      emissive: 0x059669,
      emissiveIntensity: 0.65,
      roughness: 0.12,
      metalness: 0.05,
      clearcoat: 1.0,
      clearcoatRoughness: 0.05,
      transmission: 0.15,
      ior: 1.35,
      thickness: 1.2,
      side: THREE.DoubleSide
    });
    this._disposables.push(this.positivePhaseMaterial);

    // Warm Amber / Violet (- phase) Minor Back-Lobe & Dipole Inversion
    this.negativePhaseMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xd946ef,
      emissive: 0xa21caf,
      emissiveIntensity: 0.65,
      roughness: 0.12,
      metalness: 0.05,
      clearcoat: 1.0,
      clearcoatRoughness: 0.05,
      transmission: 0.15,
      ior: 1.35,
      thickness: 1.2,
      side: THREE.DoubleSide
    });
    this._disposables.push(this.negativePhaseMaterial);

    // Unhybridized 3s Sphere Material (Sapphire Blue)
    this.sOrbitalMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x38bdf8,
      emissive: 0x0284c7,
      emissiveIntensity: 0.75,
      roughness: 0.15,
      clearcoat: 1.0,
      clearcoatRoughness: 0.04,
      transmission: 0.18,
      thickness: 1.0
    });
    this._disposables.push(this.sOrbitalMaterial);

    // Laser Caliper Arc Material: Glowing Electric Magenta / Violet
    this.caliperLineMaterial = new THREE.LineBasicMaterial({
      color: 0xd946ef,
      linewidth: 2,
      transparent: true,
      opacity: 0.95,
      blending: THREE.AdditiveBlending
    });
    this.caliperMarkerMaterial = new THREE.MeshBasicMaterial({
      color: 0xffffff
    });
    this._disposables.push(this.caliperLineMaterial, this.caliperMarkerMaterial);

    // LCAO Antibonding Nodal Plane Material (Conduction Band Ec)
    this.antibondingNodalMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xef4444,
      emissive: 0xb91c1c,
      emissiveIntensity: 0.85,
      transmission: 0.85,
      opacity: 0.45,
      transparent: true,
      roughness: 0.2,
      side: THREE.DoubleSide,
      depthWrite: false
    });
    this._disposables.push(this.antibondingNodalMaterial);
  }

  /**
   * Rule R1 Invariant: Pure, Watertight Parametric Solid Lathe Geometry
   * Generates a seamless teardrop orbital contour starting at (0,0) and closing at (0, length).
   */
  _createSolidTeardropGeometry(length, maxWidth, segments = 36) {
    const points = [];
    const steps = 30;
    for (let i = 0; i <= steps; i++) {
      const u = i / steps; // 0.0 -> 1.0
      const y = u * length;
      // Watertight cubic hermite / teardrop profile: exactly 0 at u=0 and u=1
      // Peak width occurs at u ≈ 0.62
      const r = maxWidth * Math.pow(u, 0.72) * Math.sin(Math.PI * (1.0 - u)) * 1.85;
      points.push(new THREE.Vector2(Math.max(0.0, r), y));
    }
    const geo = new THREE.LatheGeometry(points, segments);
    this._disposables.push(geo);
    return geo;
  }

  _buildBasisPedestals() {
    this.basisGroup = new THREE.Group();
    this.basisGroup.name = 'unhybridizedBasisGroup';

    const pedestalDist = 4.2;
    const lobeLen = this.options.lobeLength * 0.75;
    const lobeWidth = 0.65;

    // 1. |3s⟩ Isotropic Sphere at pedestal 0 (-X)
    this.sPedestal = new THREE.Group();
    this.sPedestal.position.set(-pedestalDist, 0, 0);
    const sGeo = new THREE.SphereGeometry(lobeWidth * 1.3, 32, 32);
    this._disposables.push(sGeo);
    const sMesh = new THREE.Mesh(sGeo, this.sOrbitalMaterial);
    this.sPedestal.add(sMesh);
    this.basisGroup.add(this.sPedestal);

    // 2. |3px⟩ Dumbbell at pedestal 1 (+X)
    this.pxPedestal = new THREE.Group();
    this.pxPedestal.position.set(pedestalDist, 0, 0);
    this._addDipoleDumbbell(this.pxPedestal, lobeLen, lobeWidth, new THREE.Vector3(1, 0, 0));
    this.basisGroup.add(this.pxPedestal);

    // 3. |3py⟩ Dumbbell at pedestal 2 (+Z)
    this.pyPedestal = new THREE.Group();
    this.pyPedestal.position.set(0, 0, pedestalDist);
    this._addDipoleDumbbell(this.pyPedestal, lobeLen, lobeWidth, new THREE.Vector3(0, 1, 0));
    this.basisGroup.add(this.pyPedestal);

    // 4. |3pz⟩ Dumbbell at pedestal 3 (-Z)
    this.pzPedestal = new THREE.Group();
    this.pzPedestal.position.set(0, 0, -pedestalDist);
    this._addDipoleDumbbell(this.pzPedestal, lobeLen, lobeWidth, new THREE.Vector3(0, 0, 1));
    this.basisGroup.add(this.pzPedestal);

    this.add(this.basisGroup);
  }

  _addDipoleDumbbell(parentGroup, length, width, axisVec) {
    const geo = this._createSolidTeardropGeometry(length, width);

    // Positive lobe (+ axis)
    const posLobe = new THREE.Mesh(geo, this.positivePhaseMaterial);
    posLobe.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), axisVec.clone().normalize());
    parentGroup.add(posLobe);

    // Negative lobe (- axis)
    const negLobe = new THREE.Mesh(geo, this.negativePhaseMaterial);
    negLobe.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), axisVec.clone().negate().normalize());
    parentGroup.add(negLobe);
  }

  _buildSp3HybridLobes() {
    this.hybridGroup = new THREE.Group();
    this.hybridGroup.name = 'sp3HybridGroup';

    // Exact tetrahedral coordinates toward alternating cube vertices:
    // (1,1,1), (1,-1,-1), (-1,1,-1), (-1,-1,1)
    const tetrahedralVectors = [
      new THREE.Vector3(1, 1, 1).normalize(),
      new THREE.Vector3(1, -1, -1).normalize(),
      new THREE.Vector3(-1, 1, -1).normalize(),
      new THREE.Vector3(-1, -1, 1).normalize()
    ];

    const majorLen = this.options.lobeLength;
    const majorWidth = 0.88;
    const minorLen = majorLen * 0.32;
    const minorWidth = 0.42;

    this.sp3Lobes = [];

    tetrahedralVectors.forEach((dir, idx) => {
      const lobeContainer = new THREE.Group();
      lobeContainer.name = `sp3_lobe_${idx}`;

      // Major positive lobe (+ phase)
      const majorGeo = this._createSolidTeardropGeometry(majorLen, majorWidth);
      const majorMesh = new THREE.Mesh(majorGeo, this.positivePhaseMaterial);
      majorMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
      lobeContainer.add(majorMesh);

      // Minor negative back-lobe (- phase) oriented directly opposite
      const minorGeo = this._createSolidTeardropGeometry(minorLen, minorWidth);
      const minorMesh = new THREE.Mesh(minorGeo, this.negativePhaseMaterial);
      minorMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().negate());
      lobeContainer.add(minorMesh);

      this.hybridGroup.add(lobeContainer);
      this.sp3Lobes.push({
        container: lobeContainer,
        direction: dir,
        majorMesh,
        minorMesh
      });
    });

    this.add(this.hybridGroup);
  }

  _buildCaliperArc() {
    this.caliperGroup = new THREE.Group();
    this.caliperGroup.name = 'laserCaliperArc';

    // Connect Lobe 0 and Lobe 1 (True 109.4712° Tetrahedral Angle)
    const dir0 = new THREE.Vector3(1, 1, 1).normalize();
    const dir1 = new THREE.Vector3(1, -1, -1).normalize();
    const arcRadius = this.options.lobeLength * 0.72;

    const segments = 48;
    const arcPoints = [];
    for (let i = 0; i <= segments; i++) {
      const alpha = i / segments;
      // Slerp along unit sphere
      const p = new THREE.Vector3().copy(dir0).lerp(dir1, alpha).normalize().multiplyScalar(arcRadius);
      arcPoints.push(p);
    }

    const arcGeo = new THREE.BufferGeometry().setFromPoints(arcPoints);
    this._disposables.push(arcGeo);
    this.caliperLine = new THREE.Line(arcGeo, this.caliperLineMaterial);
    this.caliperGroup.add(this.caliperLine);

    // Caliper snap ticks at ends
    const tickGeo = new THREE.SphereGeometry(0.045, 12, 12);
    this._disposables.push(tickGeo);
    const tick0 = new THREE.Mesh(tickGeo, this.caliperMarkerMaterial);
    tick0.position.copy(arcPoints[0]);
    const tick1 = new THREE.Mesh(tickGeo, this.caliperMarkerMaterial);
    tick1.position.copy(arcPoints[arcPoints.length - 1]);
    this.caliperGroup.add(tick0, tick1);

    // Midpoint anchor for HTML / HUD label "109.47°"
    this.caliperMidpoint = arcPoints[Math.floor(segments / 2)].clone();

    this.add(this.caliperGroup);
  }

  _buildLCAOMolecularState() {
    this.lcaoGroup = new THREE.Group();
    this.lcaoGroup.name = 'lcaoMolecularState';

    // Partner atom approaching along the (1,1,1) bond axis
    this.partnerAtomGroup = new THREE.Group();
    const bondAxis = new THREE.Vector3(1, 1, 1).normalize();

    // Constructive bonding sigma cloud (Valence band Ev)
    const bondCloudGeo = new THREE.SphereGeometry(0.85, 32, 24);
    bondCloudGeo.scale(1.0, 1.85, 1.0);
    this._disposables.push(bondCloudGeo);

    this.bondingCloudMesh = new THREE.Mesh(bondCloudGeo, this.positivePhaseMaterial);
    this.bondingCloudMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), bondAxis);
    this.lcaoGroup.add(this.bondingCloudMesh);

    // Destructive antibonding nodal plane (Conduction band Ec)
    const planeGeo = new THREE.PlaneGeometry(3.2, 3.2);
    this._disposables.push(planeGeo);
    this.antibondingPlaneMesh = new THREE.Mesh(planeGeo, this.antibondingNodalMaterial);
    this.antibondingPlaneMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), bondAxis);
    this.lcaoGroup.add(this.antibondingPlaneMesh);

    this.add(this.lcaoGroup);
  }

  /**
   * Continuous animation update
   */
  update(t, delta = 0.016) {
    // Subtle orbital phase breathing
    if (this.positivePhaseMaterial) {
      this.positivePhaseMaterial.emissiveIntensity = 0.65 + Math.sin(t * 2.5) * 0.12;
    }
    if (this.negativePhaseMaterial) {
      this.negativePhaseMaterial.emissiveIntensity = 0.65 + Math.cos(t * 2.5) * 0.12;
    }

    // Caliper arc shimmer
    if (this.caliperActive && this.caliperLineMaterial) {
      this.caliperLineMaterial.opacity = 0.85 + Math.sin(t * 4.0) * 0.15;
    }
  }

  /**
   * Smoothly interpolates between pure unhybridized basis and 100% sp³ hybrid
   * @param {number} factor - 0.0 = pure basis {|3s⟩, |3p⟩}, 1.0 = pure sp³
   */
  setHybridization(factor) {
    const f = THREE.MathUtils.clamp(factor, 0.0, 1.0);
    this.hybridizationFactor = f;

    // Basis pedestals dissolve and translate inward toward origin
    const basisP = 1.0 - f;
    this.basisGroup.visible = basisP > 0.001;
    if (this.basisGroup.visible) {
      this.basisGroup.scale.setScalar(basisP);
      this.sPedestal.position.x = -4.2 * basisP;
      this.pxPedestal.position.x = 4.2 * basisP;
      this.pyPedestal.position.z = 4.2 * basisP;
      this.pzPedestal.position.z = -4.2 * basisP;
    }

    // sp³ hybrid lobes emerge and expand outward
    this.hybridGroup.visible = f > 0.001;
    if (this.hybridGroup.visible) {
      this.hybridGroup.scale.setScalar(f * this.options.scale);
    }
  }

  /**
   * Toggles the laser caliper measurement arc (109.47°)
   */
  setCaliperActive(bool) {
    this.caliperActive = !!bool;
    this.caliperGroup.visible = this.caliperActive;
  }

  /**
   * Sets LCAO molecular orbital approach distance
   * @param {number} distance - Distance between atomic centers (5.0 = isolated, 2.35 = bonded silicon σ)
   */
  setLCAOOverlap(distance) {
    this.lcaoDistance = distance;
    const bondAxis = new THREE.Vector3(1, 1, 1).normalize();

    // Bond formation occurs when d <= 3.8
    const isOverlapping = distance < 3.8;
    this.lcaoGroup.visible = isOverlapping;

    if (isOverlapping) {
      const midPoint = bondAxis.clone().multiplyScalar(distance * 0.5);
      this.bondingCloudMesh.position.copy(midPoint);
      this.antibondingPlaneMesh.position.copy(midPoint);

      // Constructive overlap volume swells as distance closes to 2.35 Å
      const overlapWeight = THREE.MathUtils.clamp((3.8 - distance) / 1.45, 0.0, 1.0);
      this.bondingCloudMesh.scale.set(1.0 + overlapWeight * 0.4, 1.0 + overlapWeight * 0.8, 1.0 + overlapWeight * 0.4);
      this.antibondingPlaneMesh.visible = overlapWeight > 0.3;
    }
  }

  /**
   * World coordinates and metadata for dynamic 3D telemetry
   */
  getAnnotations() {
    this.updateMatrixWorld(true);

    const lobe1World = new THREE.Vector3();
    const lobe2World = new THREE.Vector3();
    if (this.sp3Lobes.length >= 2) {
      lobe1World.copy(this.sp3Lobes[0].direction).multiplyScalar(this.options.lobeLength);
      this.localToWorld(lobe1World);
      lobe2World.copy(this.sp3Lobes[1].direction).multiplyScalar(this.options.lobeLength);
      this.localToWorld(lobe2World);
    }

    const caliperWorld = this.caliperMidpoint.clone();
    this.localToWorld(caliperWorld);

    return {
      tetrahedralAngle: {
        id: 'sp3-tetrahedral-angle',
        label: '109.47° TETRAHEDRAL ANGLE',
        value: '109.47°',
        worldPosition: caliperWorld,
        caption: 'Coulomb repulsion forces electron clouds into maximum mutual separation'
      },
      majorLobe: {
        id: 'sp3-major-lobe',
        label: 'sp³ MAJOR LOBE (+)',
        worldPosition: lobe1World,
        caption: 'Constructive hybrid lobe directed along cubic vertex (1,1,1)'
      },
      sigmaBond: {
        id: 'lcao-sigma-bond',
        label: 'CONSTRUCTIVE σ BOND (Ev)',
        worldPosition: caliperWorld.clone().multiplyScalar(0.7),
        caption: 'LCAO constructive interference creating the valence band'
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
    this.sp3Lobes = [];
    this.clear();
  }
}
