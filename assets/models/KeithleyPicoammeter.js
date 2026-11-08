/**
 * IntuiSim Modular 3D Asset Library - KeithleyPicoammeter.js
 * Benchtop High-Precision Digital Picoammeter & Electrometer (Keithley 6487 standard)
 *
 * Adheres strictly to:
 * - Directive 24.5: Empirical Laboratory Instrumentation Grounding (Steve Mould / AlphaPhoenix Invariant)
 * - Directive 3: Ultra-Luxury Brushed Metal & Frosted Glass Materials
 * - Rule O1: Zero Occlusion (Positioned below or alongside crystal stage with non-blocking lead curves)
 */

import * as THREE from '../vendor/three.module.js';

export class KeithleyPicoammeter extends THREE.Group {
  /**
   * @param {Object} options
   * @param {number} [options.scale=1.0] - Overall instrument scale
   * @param {number} [options.initialCurrent=0.0] - Starting current in Amperes
   * @param {string} [options.initialUnit='nA'] - Default unit string ('A' | 'mA' | 'uA' | 'nA' | 'pA')
   * @param {boolean} [options.showProbes=true] - Generate flexible coaxial test leads
   */
  constructor(options = {}) {
    super();
    this.name = 'KeithleyPicoammeter_6487';

    this.options = Object.assign({
      scale: 1.0,
      initialCurrent: 0.0,
      initialUnit: 'nA',
      showProbes: true
    }, options);

    this.currentAmps = this.options.initialCurrent;
    this.unitStr = this.options.initialUnit;
    this.isOverload = false;
    this._disposables = [];

    this._initMaterials();
    this._buildChassis();
    this._buildFrontPanel();
    this._buildDigitalDisplay();
    this._buildTerminalsAndProbes();
    this._buildStatusLEDs();

    this.setReadout(this.currentAmps, this.unitStr);
  }

  _initMaterials() {
    // Brushed Dark Aluminum Beveled Instrument Housing
    this.chassisMaterial = new THREE.MeshStandardMaterial({
      color: 0x111827,
      roughness: 0.35,
      metalness: 0.85
    });
    this._disposables.push(this.chassisMaterial);

    // Front Panel Anodized Slate Faceplate
    this.faceplateMaterial = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      roughness: 0.45,
      metalness: 0.65
    });
    this._disposables.push(this.faceplateMaterial);

    // Protective Rubber Bumper Edges
    this.bumperMaterial = new THREE.MeshStandardMaterial({
      color: 0x0a0f1d,
      roughness: 0.9,
      metalness: 0.1
    });
    this._disposables.push(this.bumperMaterial);

    // Gold-Plated Triaxial Terminal BNC Jacks
    this.goldTerminalMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xd4af37,
      emissive: 0x854d0e,
      emissiveIntensity: 0.25,
      roughness: 0.15,
      metalness: 0.95,
      clearcoat: 1.0,
      clearcoatRoughness: 0.04
    });
    this._disposables.push(this.goldTerminalMaterial);

    // High (Red/Amber) and Low (Black/Obsidian) Probe Lead Sheaths
    this.leadHiMaterial = new THREE.MeshStandardMaterial({
      color: 0xef4444,
      roughness: 0.3,
      metalness: 0.2
    });
    this.leadLoMaterial = new THREE.MeshStandardMaterial({
      color: 0x0284c7,
      roughness: 0.3,
      metalness: 0.2
    });
    this._disposables.push(this.leadHiMaterial, this.leadLoMaterial);

    // Status Annunciator LED Materials
    this.ledPowerMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
    this.ledZeroMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });
    this.ledOverloadMat = new THREE.MeshBasicMaterial({ color: 0x334155 }); // Inactive by default
    this.ledRemoteMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    this._disposables.push(this.ledPowerMat, this.ledZeroMat, this.ledOverloadMat, this.ledRemoteMat);
  }

  _buildChassis() {
    this.chassisGroup = new THREE.Group();

    const w = 4.4;
    const h = 1.7;
    const d = 3.6;

    // Main Box Enclosure
    const boxGeo = new THREE.BoxGeometry(w, h, d);
    this._disposables.push(boxGeo);
    const boxMesh = new THREE.Mesh(boxGeo, this.chassisMaterial);
    this.chassisGroup.add(boxMesh);

    // Corner Rubber Protective Caps (4 corners)
    const bumperGeo = new THREE.BoxGeometry(0.25, h + 0.05, 0.25);
    this._disposables.push(bumperGeo);
    const offsets = [
      [-w / 2, 0, -d / 2],
      [w / 2, 0, -d / 2],
      [-w / 2, 0, d / 2],
      [w / 2, 0, d / 2]
    ];
    offsets.forEach(([bx, by, bz]) => {
      const bMesh = new THREE.Mesh(bumperGeo, this.bumperMaterial);
      bMesh.position.set(bx, by, bz);
      this.chassisGroup.add(bMesh);
    });

    // Tilt Handle Bail
    const handleGeo = new THREE.TorusGeometry(1.6, 0.06, 12, 32, Math.PI);
    this._disposables.push(handleGeo);
    const handleMesh = new THREE.Mesh(handleGeo, this.chassisMaterial);
    handleMesh.position.set(0, 0, -d / 2 + 0.2);
    handleMesh.rotation.x = Math.PI / 2;
    this.chassisGroup.add(handleMesh);

    this.add(this.chassisGroup);
  }

  _buildFrontPanel() {
    this.panelGroup = new THREE.Group();
    const w = 4.3;
    const h = 1.6;
    const d = 3.6;

    const panelGeo = new THREE.PlaneGeometry(w, h);
    this._disposables.push(panelGeo);
    const panelMesh = new THREE.Mesh(panelGeo, this.faceplateMaterial);
    panelMesh.position.set(0, 0, d / 2 + 0.01);
    this.panelGroup.add(panelMesh);

    // Power Rocker Switch
    const switchGeo = new THREE.BoxGeometry(0.3, 0.2, 0.12);
    const switchMat = new THREE.MeshStandardMaterial({ color: 0xef4444, roughness: 0.4 });
    this._disposables.push(switchGeo, switchMat);
    const switchMesh = new THREE.Mesh(switchGeo, switchMat);
    switchMesh.position.set(-1.7, -0.45, d / 2 + 0.07);
    this.panelGroup.add(switchMesh);

    this.add(this.panelGroup);
  }

  _buildDigitalDisplay() {
    // Dynamic 512x128 HTML5 Canvas for Live High-Contrast Vacuum Fluorescent / LED Readout
    this.displayCanvas = document.createElement('canvas');
    this.displayCanvas.width = 512;
    this.displayCanvas.height = 128;
    this.displayCtx = this.displayCanvas.getContext('2d');

    this.displayTexture = new THREE.CanvasTexture(this.displayCanvas);
    this.displayTexture.minFilter = THREE.LinearFilter;
    this._disposables.push(this.displayTexture);

    this.displayMaterial = new THREE.MeshBasicMaterial({
      map: this.displayTexture,
      transparent: false
    });
    this._disposables.push(this.displayMaterial);

    const dispGeo = new THREE.PlaneGeometry(2.4, 0.65);
    this._disposables.push(dispGeo);
    this.displayMesh = new THREE.Mesh(dispGeo, this.displayMaterial);
    this.displayMesh.position.set(-0.65, 0.28, 3.6 / 2 + 0.02);
    this.add(this.displayMesh);
  }

  _buildTerminalsAndProbes() {
    this.terminalsGroup = new THREE.Group();
    const dZ = 3.6 / 2 + 0.15;

    // High (HI) Triaxial Jack
    const jackGeo = new THREE.CylinderGeometry(0.16, 0.16, 0.25, 24);
    jackGeo.rotateX(Math.PI / 2);
    this._disposables.push(jackGeo);

    this.hiJack = new THREE.Mesh(jackGeo, this.goldTerminalMaterial);
    this.hiJack.position.set(1.3, 0.25, dZ);
    this.terminalsGroup.add(this.hiJack);

    // Low (LO) Triaxial Jack
    this.loJack = new THREE.Mesh(jackGeo, this.goldTerminalMaterial);
    this.loJack.position.set(1.3, -0.32, dZ);
    this.terminalsGroup.add(this.loJack);

    // Flexible Test Leads (Curved Splines curving forward toward specimen)
    if (this.options.showProbes) {
      this._buildFlexibleLead(new THREE.Vector3(1.3, 0.25, dZ), new THREE.Vector3(2.5, 1.2, 3.5), this.leadHiMaterial, true);
      this._buildFlexibleLead(new THREE.Vector3(1.3, -0.32, dZ), new THREE.Vector3(2.2, -0.8, 3.5), this.leadLoMaterial, false);
    }

    this.add(this.terminalsGroup);
  }

  _buildFlexibleLead(startPos, endPos, material, isHi) {
    const mid1 = startPos.clone().add(new THREE.Vector3(0.5, 0, 0.8));
    const mid2 = endPos.clone().add(new THREE.Vector3(-0.6, 0, -0.8));

    const curve = new THREE.CubicBezierCurve3(startPos, mid1, mid2, endPos);
    const tubeGeo = new THREE.TubeGeometry(curve, 32, 0.042, 12, false);
    this._disposables.push(tubeGeo);

    const tubeMesh = new THREE.Mesh(tubeGeo, material);
    this.terminalsGroup.add(tubeMesh);

    // Golden Probe Tip Pin
    const pinGeo = new THREE.CylinderGeometry(0.015, 0.035, 0.35, 12);
    pinGeo.rotateX(Math.PI / 2);
    this._disposables.push(pinGeo);

    const pinMesh = new THREE.Mesh(pinGeo, this.goldTerminalMaterial);
    pinMesh.position.copy(endPos);
    this.terminalsGroup.add(pinMesh);

    if (isHi) this.hiProbeTip = pinMesh;
    else this.loProbeTip = pinMesh;
  }

  _buildStatusLEDs() {
    this.ledGroup = new THREE.Group();
    const dZ = 3.6 / 2 + 0.025;
    const ledGeo = new THREE.CircleGeometry(0.045, 16);
    this._disposables.push(ledGeo);

    const leds = [
      { mat: this.ledPowerMat, x: -1.7, y: 0.42, name: 'POWER' },
      { mat: this.ledZeroMat, x: -1.4, y: 0.42, name: 'ZERO' },
      { mat: this.ledOverloadMat, x: -1.1, y: 0.42, name: 'OVERLOAD' },
      { mat: this.ledRemoteMat, x: -0.8, y: 0.42, name: 'REMOTE' }
    ];

    leds.forEach(l => {
      const mesh = new THREE.Mesh(ledGeo, l.mat);
      mesh.position.set(l.x, l.y, dZ);
      this.ledGroup.add(mesh);
    });

    this.add(this.ledGroup);
  }

  /**
   * Continuous animation update
   */
  update(t, delta = 0.016) {
    // Subtle digital phosphor flicker
    if (this.displayTexture && !this.isOverload) {
      if (Math.random() < 0.03) {
        this.displayTexture.needsUpdate = true;
      }
    }
  }

  /**
   * Updates digital 7-segment readout with calibrated SI formatting
   * @param {number} currentAmps - Current value in Amperes
   * @param {string} [unitStr] - Optional unit override ('nA', 'pA', 'A')
   */
  setReadout(currentAmps, unitStr) {
    this.currentAmps = currentAmps;
    this.isOverload = false;
    this.ledOverloadMat.color.setHex(0x334155); // Inactive

    let displayVal = '';
    let unit = unitStr || 'nA';

    if (!unitStr) {
      const absA = Math.abs(currentAmps);
      if (absA >= 1e-3) {
        unit = 'mA';
        displayVal = (currentAmps * 1e3).toFixed(5);
      } else if (absA >= 1e-6) {
        unit = 'μA';
        displayVal = (currentAmps * 1e6).toFixed(5);
      } else if (absA >= 1e-9) {
        unit = 'nA';
        displayVal = (currentAmps * 1e9).toFixed(5);
      } else {
        unit = 'pA';
        displayVal = (currentAmps * 1e12).toFixed(5);
      }
    } else {
      if (unit === 'nA') displayVal = (currentAmps * 1e9).toFixed(5);
      else if (unit === 'pA') displayVal = (currentAmps * 1e12).toFixed(5);
      else if (unit === 'uA' || unit === 'μA') displayVal = (currentAmps * 1e6).toFixed(5);
      else displayVal = currentAmps.toExponential(6);
    }

    const sign = currentAmps >= 0 ? '+' : '';
    this._renderCanvasText(`${sign}${displayVal} ${unit}`);
  }

  /**
   * Triggers instrument overload state
   */
  setOverload(bool = true) {
    this.isOverload = !!bool;
    if (this.isOverload) {
      this.ledOverloadMat.color.setHex(0xef4444); // Radiant red
      this._renderCanvasText('OVERFLOW !!', '#ef4444');
    } else {
      this.setReadout(this.currentAmps, this.unitStr);
    }
  }

  _renderCanvasText(text, glowColor = '#00ffcc') {
    const ctx = this.displayCtx;
    const w = this.displayCanvas.width;
    const h = this.displayCanvas.height;

    // Dark VFD phosphor background
    ctx.fillStyle = '#03080d';
    ctx.fillRect(0, 0, w, h);

    // Bezel border
    ctx.strokeStyle = '#0e2433';
    ctx.lineWidth = 4;
    ctx.strokeRect(4, 4, w - 8, h - 8);

    // Instrument header silk-screen
    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 18px "JetBrains Mono", monospace';
    ctx.fillText('KEITHLEY 6487  AUTO-RANGE PICOAMMETER', 24, 32);

    // Glowing main readout
    ctx.shadowColor = glowColor;
    ctx.shadowBlur = 14;
    ctx.fillStyle = glowColor;
    ctx.font = 'bold 46px "JetBrains Mono", monospace';
    ctx.fillText(text, 24, 94);

    ctx.shadowBlur = 0;
    this.displayTexture.needsUpdate = true;
  }

  /**
   * Returns world-space positions of high/low probe tips for attaching to crystal electrodes
   */
  getTerminalsPosition() {
    this.updateMatrixWorld(true);

    const hiWorld = new THREE.Vector3();
    const loWorld = new THREE.Vector3();

    if (this.hiProbeTip) this.hiProbeTip.getWorldPosition(hiWorld);
    else this.hiJack.getWorldPosition(hiWorld);

    if (this.loProbeTip) this.loProbeTip.getWorldPosition(loWorld);
    else this.loJack.getWorldPosition(loWorld);

    return {
      hiTerminal: hiWorld,
      loTerminal: loWorld
    };
  }

  dispose() {
    this._disposables.forEach(item => {
      if (item && typeof item.dispose === 'function') {
        item.dispose();
      }
    });
    this._disposables = [];
    this.clear();
  }
}
