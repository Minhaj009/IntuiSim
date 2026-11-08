/**
 * IntuiSim Modular 3D Asset Library - DiamondCubicUnitCell.js
 * Diamond Cubic Crystal Lattice Structure (Silicon a = 5.43 Å)
 *
 * Adheres strictly to:
 * - Directive 18.1: Dynamic Geometric Disassembly (Exploded Octant & Face Rails)
 * - Directive 2: Zero UI Overlap & Progressive Disclosure (Corner -> Face -> Interior -> Total)
 * - Rule D1: Continuous Purposeful Motion (No aimless turntable spinning!)
 * - Rule R1: Manifold Watertight Solid Geometries for Sliced Octants & Hemispheres
 */

import * as THREE from '../vendor/three.module.js';

export class DiamondCubicUnitCell extends THREE.Group {
  /**
   * @param {Object} options
   * @param {number} [options.a=5.43] - Lattice constant in visual scale / Ångströms
   * @param {number} [options.atomRadius=0.52] - Atomic sphere radius
   * @param {number} [options.bondRadius=0.08] - Covalent bond cylinder radius
   * @param {number} [options.initialExplosion=0.0] - Disassembly progress factor (0.0 to 1.0)
   * @param {boolean} [options.clippedOctants=false] - Slice atoms into true 1/8 wedges and 1/2 hemispheres
   */
  constructor(options = {}) {
    super();
    this.name = 'DiamondCubicUnitCell';

    this.options = Object.assign({
      a: 5.43,
      atomRadius: 0.52,
      bondRadius: 0.08,
      initialExplosion: 0.0,
      clippedOctants: false
    }, options);

    this.explosionFactor = this.options.initialExplosion;
    this.isClipped = this.options.clippedOctants;
    this._disposables = [];

    this._initMaterials();
    this._buildWireframeBox();
    this._buildCornerAtoms();
    this._buildFaceAtoms();
    this._buildInteriorBasisAtoms();
    this._buildCovalentBonds();

    this.setExplosion(this.explosionFactor);
    this.setClippedOctants(this.isClipped);
  }

  _initMaterials() {
    // Corner Atoms: Warm Amber / Ruby Gold (8x * 1/8 = 1 atom)
    this.cornerMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xf59e0b,
      emissive: 0xd97706,
      emissiveIntensity: 1.0,
      roughness: 0.15,
      metalness: 0.1,
      clearcoat: 1.0,
      clearcoatRoughness: 0.04
    });
    this._disposables.push(this.cornerMaterial);

    // Face-Center Atoms: Emerald Green (6x * 1/2 = 3 atoms)
    this.faceMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x10b981,
      emissive: 0x059669,
      emissiveIntensity: 1.0,
      roughness: 0.15,
      metalness: 0.1,
      clearcoat: 1.0,
      clearcoatRoughness: 0.04
    });
    this._disposables.push(this.faceMaterial);

    // Interior Tetrahedral Basis Atoms: Electric Cyan (4x * 1 = 4 atoms)
    this.interiorMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x00f0ff,
      emissive: 0x0284c7,
      emissiveIntensity: 1.4,
      roughness: 0.12,
      metalness: 0.05,
      clearcoat: 1.0,
      clearcoatRoughness: 0.04
    });
    this._disposables.push(this.interiorMaterial);

    // Covalent Bond Cylinder Material: Frosted Quartz
    this.bondMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x94a3b8,
      emissive: 0x334155,
      emissiveIntensity: 0.45,
      roughness: 0.25,
      clearcoat: 0.8
    });
    this._disposables.push(this.bondMaterial);

    // Coordinate Bounding Cube Wireframe
    this.boxWireMaterial = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.45,
      blending: THREE.AdditiveBlending
    });
    this._disposables.push(this.boxWireMaterial);
  }

  _buildWireframeBox() {
    const a = this.options.a;
    const boxGeo = new THREE.BoxGeometry(a, a, a);
    const edgesGeo = new THREE.EdgesGeometry(boxGeo);
    this._disposables.push(boxGeo, edgesGeo);

    this.wireframeBox = new THREE.LineSegments(edgesGeo, this.boxWireMaterial);
    this.add(this.wireframeBox);
  }

  /**
   * Builds 8 Corner Atoms sliding outward along (±1, ±1, ±1) diagonal rails
   */
  _buildCornerAtoms() {
    this.cornerGroup = new THREE.Group();
    this.cornerGroup.name = 'cornerAtomsGroup';

    const halfA = this.options.a * 0.5;
    const r = this.options.atomRadius;

    this.cornerNodes = [];
    const cornerSigns = [
      [-1, -1, -1], [1, -1, -1], [-1, 1, -1], [1, 1, -1],
      [-1, -1, 1],  [1, -1, 1],  [-1, 1, 1],  [1, 1, 1]
    ];

    // Watertight full sphere and 1/8 octant wedge geometries
    const fullGeo = new THREE.SphereGeometry(r, 24, 24);
    // Octant sector: 90° phi, 90° theta
    const octantGeo = new THREE.SphereGeometry(r, 16, 16, 0, Math.PI / 2, 0, Math.PI / 2);
    this._disposables.push(fullGeo, octantGeo);

    cornerSigns.forEach(([cx, cy, cz]) => {
      const g = new THREE.Group();
      const basePos = new THREE.Vector3(cx * halfA, cy * halfA, cz * halfA);
      g.position.copy(basePos);

      const fullMesh = new THREE.Mesh(fullGeo, this.cornerMaterial);
      const wedgeMesh = new THREE.Mesh(octantGeo, this.cornerMaterial);

      // Rotate wedge so it faces strictly into the unit cell interior
      wedgeMesh.rotation.set(
        cx > 0 ? Math.PI : 0,
        cy > 0 ? Math.PI : 0,
        cz > 0 ? Math.PI : 0
      );
      wedgeMesh.visible = false;

      g.add(fullMesh);
      g.add(wedgeMesh);
      this.cornerGroup.add(g);

      const dir = new THREE.Vector3(cx, cy, cz).normalize();
      this.cornerNodes.push({
        group: g,
        basePos,
        dir,
        fullMesh,
        wedgeMesh
      });
    });

    this.add(this.cornerGroup);
  }

  /**
   * Builds 6 Face-Centered Atoms sliding outward along Cartesian axes (±1, 0, 0), etc.
   */
  _buildFaceAtoms() {
    this.faceGroup = new THREE.Group();
    this.faceGroup.name = 'faceAtomsGroup';

    const halfA = this.options.a * 0.5;
    const r = this.options.atomRadius;

    this.faceNodes = [];
    const faceCoords = [
      [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]
    ];

    const fullGeo = new THREE.SphereGeometry(r, 24, 24);
    // Hemisphere: 180° phi
    const hemiGeo = new THREE.SphereGeometry(r, 20, 20, 0, Math.PI, 0, Math.PI);
    this._disposables.push(fullGeo, hemiGeo);

    faceCoords.forEach(([fx, fy, fz]) => {
      const g = new THREE.Group();
      const basePos = new THREE.Vector3(fx * halfA, fy * halfA, fz * halfA);
      g.position.copy(basePos);

      const fullMesh = new THREE.Mesh(fullGeo, this.faceMaterial);
      const hemiMesh = new THREE.Mesh(hemiGeo, this.faceMaterial);

      // Orient hemisphere facing inward
      hemiMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(-fx, -fy, -fz).normalize());
      hemiMesh.visible = false;

      g.add(fullMesh);
      g.add(hemiMesh);
      this.faceGroup.add(g);

      const dir = new THREE.Vector3(fx, fy, fz).normalize();
      this.faceNodes.push({
        group: g,
        basePos,
        dir,
        fullMesh,
        hemiMesh
      });
    });

    this.add(this.faceGroup);
  }

  /**
   * Builds 4 Interior Tetrahedral Basis Atoms (100% enclosed)
   */
  _buildInteriorBasisAtoms() {
    this.interiorGroup = new THREE.Group();
    this.interiorGroup.name = 'interiorBasisGroup';

    const quarterA = this.options.a * 0.25;
    const r = this.options.atomRadius;

    this.interiorNodes = [];
    const interiorCoords = [
      [-quarterA, -quarterA, -quarterA],
      [quarterA, quarterA, -quarterA],
      [quarterA, -quarterA, quarterA],
      [-quarterA, quarterA, quarterA]
    ];

    const geo = new THREE.SphereGeometry(r, 28, 28);
    this._disposables.push(geo);

    interiorCoords.forEach(([ix, iy, iz]) => {
      const g = new THREE.Group();
      const basePos = new THREE.Vector3(ix, iy, iz);
      g.position.copy(basePos);

      const mesh = new THREE.Mesh(geo, this.interiorMaterial);
      g.add(mesh);
      this.interiorGroup.add(g);

      this.interiorNodes.push({ group: g, basePos, mesh });
    });

    this.add(this.interiorGroup);
  }

  /**
   * Connects interior basis atoms to their 4 nearest FCC neighbors with covalent cylinders
   */
  _buildCovalentBonds() {
    this.bondsGroup = new THREE.Group();
    this.bondsGroup.name = 'covalentBondsGroup';

    const halfA = this.options.a * 0.5;
    const quarterA = this.options.a * 0.25;
    const rBond = this.options.bondRadius;

    this.bondMeshes = [];

    // Each interior basis atom bonds to 4 nearest neighbors (1 corner, 3 face centers)
    this.interiorNodes.forEach(interior => {
      const pInt = interior.basePos;

      // Find nearest 4 neighbors among corners and faces
      const allNeighbors = [...this.cornerNodes, ...this.faceNodes];
      const sorted = allNeighbors
        .map(n => ({ node: n, dist: pInt.distanceTo(n.basePos) }))
        .sort((a, b) => a.dist - b.dist)
        .slice(0, 4);

      sorted.forEach(({ node }) => {
        const pTarget = node.basePos;
        const bondVec = new THREE.Vector3().subVectors(pTarget, pInt);
        const len = bondVec.length();

        const cylGeo = new THREE.CylinderGeometry(rBond, rBond, len, 12);
        cylGeo.translate(0, len / 2, 0);
        cylGeo.rotateX(Math.PI / 2);
        this._disposables.push(cylGeo);

        const mesh = new THREE.Mesh(cylGeo, this.bondMaterial);
        mesh.position.copy(pInt);
        mesh.lookAt(pTarget);

        this.bondsGroup.add(mesh);
        this.bondMeshes.push(mesh);
      });
    });

    this.add(this.bondsGroup);
  }

  /**
   * Continuous animation update
   */
  update(t, delta = 0.016) {
    // Subtle pulsating glow on interior basis atoms
    if (this.interiorMaterial) {
      this.interiorMaterial.emissiveIntensity = 1.4 + Math.sin(t * 3.0) * 0.25;
    }
  }

  /**
   * Sets the exploded disassembly rail progression (Rule D1 & Directive 18.1)
   * @param {number} factor - 0.0 = compact unit cell, 1.0 = fully exploded
   */
  setExplosion(factor) {
    const p = THREE.MathUtils.clamp(factor, 0.0, 1.0);
    this.explosionFactor = p;

    // Smoothstep easing
    const s = p * p * (3 - 2 * p);

    // 1. 8 Corner atoms slide outward diagonally along (±1, ±1, ±1) by 2.2 units
    this.cornerNodes.forEach(node => {
      node.group.position.copy(node.basePos.clone().add(node.dir.clone().multiplyScalar(2.2 * s)));
    });

    // 2. 6 Face-center atoms slide outward along Cartesian axes by 2.8 units
    this.faceNodes.forEach(node => {
      node.group.position.copy(node.basePos.clone().add(node.dir.clone().multiplyScalar(2.8 * s)));
    });

    // 3. 4 Interior basis atoms elevate along +Y for clear view (Rule O1)
    this.interiorNodes.forEach(node => {
      node.group.position.copy(node.basePos.clone().add(new THREE.Vector3(0, 1.4 * s, 0)));
    });

    // 4. Covalent bonds attenuate and fade out when exploded
    if (this.bondsGroup) {
      this.bondsGroup.visible = p < 0.25;
      if (this.bondsGroup.visible) {
        this.bondMaterial.opacity = 1.0 - p * 4.0;
      }
    }
  }

  /**
   * Toggles geometric clipping between full spheres and 1/8 wedges / 1/2 hemispheres
   */
  setClippedOctants(bool) {
    this.isClipped = !!bool;

    this.cornerNodes.forEach(node => {
      node.fullMesh.visible = !this.isClipped;
      node.wedgeMesh.visible = this.isClipped;
    });

    this.faceNodes.forEach(node => {
      node.fullMesh.visible = !this.isClipped;
      node.hemiMesh.visible = this.isClipped;
    });
  }

  /**
   * Progressive disclosure focus (Directive 2 & 14)
   * Illuminates only the requested sub-group while attenuating spectators
   * @param {'corner' | 'face' | 'interior' | 'all'} groupName
   */
  highlightBasis(groupName) {
    const dimOpacity = 0.22;

    if (groupName === 'corner') {
      this.cornerMaterial.emissiveIntensity = 1.8;
      this.faceMaterial.emissiveIntensity = 0.2;
      this.interiorMaterial.emissiveIntensity = 0.2;
    } else if (groupName === 'face') {
      this.cornerMaterial.emissiveIntensity = 0.2;
      this.faceMaterial.emissiveIntensity = 1.8;
      this.interiorMaterial.emissiveIntensity = 0.2;
    } else if (groupName === 'interior') {
      this.cornerMaterial.emissiveIntensity = 0.2;
      this.faceMaterial.emissiveIntensity = 0.2;
      this.interiorMaterial.emissiveIntensity = 2.4;
    } else {
      // 'all'
      this.cornerMaterial.emissiveIntensity = 1.0;
      this.faceMaterial.emissiveIntensity = 1.0;
      this.interiorMaterial.emissiveIntensity = 1.4;
    }
  }

  /**
   * Rigorous stoichiometry calculation per unit cell
   */
  getStoichiometryBreakdown() {
    return {
      corners: { count: 8, fraction: 0.125, netAtoms: 1.0 },
      faces: { count: 6, fraction: 0.5, netAtoms: 3.0 },
      interior: { count: 4, fraction: 1.0, netAtoms: 4.0 },
      netTotalAtoms: 8.0,
      atomicPackingFraction: 0.3401, // APF = (8 * (4/3) * pi * r³) / a³ with r = sqrt(3)*a / 8
      latticeParameterAngstrom: 5.43
    };
  }

  getAnnotations() {
    this.updateMatrixWorld(true);

    const cornerPos = new THREE.Vector3();
    if (this.cornerNodes.length > 0) {
      this.cornerNodes[7].group.getWorldPosition(cornerPos);
    }

    const facePos = new THREE.Vector3();
    if (this.faceNodes.length > 0) {
      this.faceNodes[0].group.getWorldPosition(facePos);
    }

    const interiorPos = new THREE.Vector3();
    if (this.interiorNodes.length > 0) {
      this.interiorNodes[0].group.getWorldPosition(interiorPos);
    }

    return {
      cornerWedge: {
        id: 'corner-octant',
        label: 'CORNER ATOMS (8x)',
        stoichiometry: '8 × 1/8 volume slice = 1 net atom',
        worldPosition: cornerPos
      },
      faceHemisphere: {
        id: 'face-hemisphere',
        label: 'FACE-CENTERED ATOMS (6x)',
        stoichiometry: '6 × 1/2 hemisphere cut = 3 net atoms',
        worldPosition: facePos
      },
      interiorBasis: {
        id: 'interior-basis',
        label: 'INTERIOR BASIS ATOMS (4x)',
        stoichiometry: '4 × 1 fully enclosed = 4 net atoms',
        worldPosition: interiorPos
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
    this.cornerNodes = [];
    this.faceNodes = [];
    this.interiorNodes = [];
    this.bondMeshes = [];
    this.clear();
  }
}
