# IntuiSim Modular 3D Asset Library

> **Production-Grade Three.js Simulation Assets for Autonomous Video Production & SaaS Simulation Engine**

[![Three.js r169](https://img.shields.io/badge/Three.js-r169-black.svg)](https://threejs.org)
[![GLTF 2.0](https://img.shields.io/badge/Asset%20Format-GLTF%20%2F%20GLB-green.svg)](https://www.khronos.org/gltf/)
[![Aesthetics](https://img.shields.io/badge/Aesthetics-Linear%20%2F%20Apple%20Keynote-blue.svg)](https://linear.app)

---

## 1. Architectural Philosophy

The **IntuiSim Modular 3D Asset Library** provides reusable, highly performant Three.js ES6 classes engineered to power both autonomous 60fps STEM documentary video pipelines and next-generation interactive simulation software.

Each asset is engineered around four core invariants:
1. **Rule D1 (Exploded Anatomical Dissection):** No continuous, purposeless turntable spinning. Every composite model implements calibrated disassembly rails, laser-cutting planes, or geometric unrolling synchronized with Whisper word cues (`window.__SCENE_CUES__`).
2. **Rule R1 (Manifold Watertight Solid Geometries):** Orbital lobes and sliced atomic components are generated using closed parametric lathe profiles and explicit sector caps. Zero hollow clipped shells or unbounded local clipping planes.
3. **Rule O1 (Zero Occlusion):** Transparent micro-meshes, transmission materials (`transmission: 0.15 - 0.85`), and elevated Z/Y offsets guarantee that internal features and data telemetry remain 100% visible from all camera perspectives.
4. **Directive 3 (Ultra-Luxury Materiality):** Models employ physical materials (`MeshPhysicalMaterial`) featuring cool specular highlights, deep transmission, clearcoat sheen (`clearcoat: 1.0, clearcoatRoughness: 0.04`), and subtle subsurface emissivity.

---

## 2. Directory Structure

```
F:\IntuiSim\assets\
├── models\
│   ├── SiliconAtom.js            # Isolated Silicon atom with neon core & valence rails
│   ├── Sp3OrbitalGroup.js        # Solid lathe hybrid orbitals & 109.47° laser caliper
│   ├── KeithleyPicoammeter.js    # Benchtop picoammeter with live digital display & test probes
│   ├── ModelExporter.js          # Standalone GLTF/GLB/JSON client and headless exporter
│   └── registry.json             # Master JSON catalog with schemas and REST/GraphQL specs
├── structures\
│   ├── DiamondCubicUnitCell.js   # Diamond cubic lattice with 1/8 octant wedges & stoichiometry
│   └── PotentialWellTerrain.js   # Kronig-Penney 3D energy landscape & Bloch wavepacket
└── vendor\
    ├── three.module.js           # Three.js r169 core bundle
    └── three\addons\exporters\   # Three.js GLTFExporter addons
```

---

## 3. Asset Specifications & Control APIs

### A. `SiliconAtom.js`
Represents an isolated Silicon atom ($Z=14$) with distinct quantum shells:
- **`nucleusGroup`:** Central glowing $+14q$ core sphere with amber clearcoat glow.
- **`coreShellsGroup`:** Neon-like core $[1s^2 2s^2 2p^6]$ (10 electrons) sliding along $+X$ axial rail.
- **`valenceGroup`:** Reactive outer M-shell ($n=3$, $3s^2 3p^2$) sliding along $-X$ axial rail.
- **`nodalPlanesGroup`:** Concentric spherical shells representing the 2 radial nodes of $3s$ ($n - l - 1 = 2$).
- **`laserSlicePlane`:** Translucent glowing sweep plane with animated emissive edge.

```javascript
import { SiliconAtom } from './assets/models/SiliconAtom.js';

const atom = new SiliconAtom({
  radius: 1.5,
  coreRadius: 0.7,
  valenceRadius: 2.4,
  showRadialNodes: false,
  laserPlaneActive: false,
  materialStyle: 'luxury'
});
scene.add(atom);

// Dynamic Animation Stepper
atom.setDisassemblyRail(0.85);          // Decouple neon core (+X) and valence shell (-X)
atom.setRadialNodesVisible(true);        // Expose zero-probability shells
atom.setLaserPlane(0.5, true);          // Slice cross-section at y = 0.5
atom.update(currentTime, deltaTime);
```

### B. `Sp3OrbitalGroup.js`
Visualizes atomic and hybrid orbitals using pure parametric lathe teardrop geometry:
- **Watertight Parametric Solid:** Cubic hermite contour strictly non-hollow with zero clipping artifacts.
- **Basis Pedestals:** Distinct $|3s\rangle$ sphere and $\{|3p_x\rangle, |3p_y\rangle, |3p_z\rangle\}$ dumbbells that smoothly translate and morph into the interaction cube.
- **Four $sp^3$ Hybrid Lobes:** Directed toward alternating cube vertices $(1,1,1), (1,-1,-1), (-1,1,-1), (-1,-1,1)$.
- **Dynamic Laser Caliper Arc:** 3D spline arc connecting Lobe 1 to Lobe 2 with angle label anchor ($109.47^\circ$).
- **LCAO Molecular State:** Partner atom approaching along $(1,1,1)$ axis forming constructive bonding cloud $\psi_\sigma$ ($E_v$) vs antibonding nodal plane $\psi_\sigma^*$ ($E_c$).

```javascript
import { Sp3OrbitalGroup } from './assets/models/Sp3OrbitalGroup.js';

const orbitals = new Sp3OrbitalGroup({ lobeLength: 2.8, hybridization: 0.0 });
scene.add(orbitals);

orbitals.setHybridization(1.0);         // Smoothly transition from basis to sp³ hybrid
orbitals.setCaliperActive(true);        // Display glowing 109.47° dimension caliper
orbitals.setLCAOOverlap(2.35);          // Form covalent σ bond with partner atom
```

### C. `KeithleyPicoammeter.js`
High-precision laboratory instrument model (Keithley 6487):
- **Chassis:** Beveled dark aluminum housing with rubber bumpers and tilt handle.
- **Live 7-Segment VFD Display:** Dynamic HTML5 canvas texture updating with automatic SI prefixing.
- **Gold Triaxial Terminals & Probes:** Flexible Bézier coaxial test leads attaching to crystal contacts.
- **Status Indicators:** POWER, ZERO CHECK, OVERLOAD, REMOTE annunciator LEDs.

```javascript
import { KeithleyPicoammeter } from './assets/models/KeithleyPicoammeter.js';

const ammeter = new KeithleyPicoammeter({ initialCurrent: 12.4e-9 });
scene.add(ammeter);

ammeter.setReadout(14.82e-9, 'nA');     // Updates digital display to "+14.82000 nA"
ammeter.setOverload(true);              // Triggers radiant red "OVERFLOW" and LED
const { hiTerminal, loTerminal } = ammeter.getTerminalsPosition();
```

### D. `DiamondCubicUnitCell.js`
Diamond cubic crystal unit cell ($a = 5.43$ Å):
- **Corner Atoms (8x):** Sliced into true $1/8$ octant wedges locked inside cube corners ($8 \times 1/8 = 1$).
- **Face Atoms (6x):** Sliced into true $1/2$ hemispheres along boundary planes ($6 \times 1/2 = 3$).
- **Interior Basis (4x):** Fully enclosed tetrahedral cages ($4 \times 1 = 4$). Net total: 8 atoms, $\text{APF} = 0.3401$.
- **Disassembly Rails:** Corner atoms slide outward diagonally along $(\pm 1, \pm 1, \pm 1)$, face atoms along Cartesian axes, interior atoms elevate along $+Y$.

```javascript
import { DiamondCubicUnitCell } from './assets/structures/DiamondCubicUnitCell.js';

const unitCell = new DiamondCubicUnitCell({ a: 5.43 });
scene.add(unitCell);

unitCell.setExplosion(0.75);            // Explode along crystallographic rails
unitCell.setClippedOctants(true);        // Morph full spheres into 1/8 wedges & 1/2 hemispheres
unitCell.highlightBasis('corner');      // Focus solely on corner stoichiometry
const stats = unitCell.getStoichiometryBreakdown(); // { corners: 1, faces: 3, interior: 4, total: 8, apf: 0.3401 }
```

### E. `PotentialWellTerrain.js`
Continuous 3D Kronig-Penney potential energy landscape $V(x,z)$:
- **Topography:** Deep Coulomb attractive wells at lattice sites and periodic barrier peaks between them.
- **Bloch Wavepacket:** Localized 3D Gaussian wavepacket $\psi_k(\mathbf{r}, t)$ gliding across potential wells with phase interference fringes.
- **Thermal Phonons:** Dynamic acoustic phonon superposition waves scaling from $0\text{ K}$ (cryogenic freeze) to $300\text{ K}$ (room temperature agitation).

```javascript
import { PotentialWellTerrain } from './assets/structures/PotentialWellTerrain.js';

const terrain = new PotentialWellTerrain({ latticeConstant: 3.2 });
scene.add(terrain);

terrain.setTemperature(300.0);          // Drive thermal phonon agitation to 300 K
terrain.setWavepacketPosition(2.4, 1.2); // Position carrier wavepacket on potential contour
terrain.update(currentTime, deltaTime);
```

---

## 4. GLTF / GLB Export Workflow (`ModelExporter.js`)

SaaS users can serialize and download any customized atomic, molecular, or structural state directly as standard `.glb` assets:

```javascript
import { ModelExporter } from './assets/models/ModelExporter.js';

// Export an exploded unit cell
await ModelExporter.exportToGLB(unitCell, 'silicon_unit_cell_exploded.glb', {
  binary: true,
  maxTextureSize: 2048
});

// Or export complete scene hierarchy to JSON
const sceneJson = ModelExporter.exportToJSON(atom, 'silicon_atom_state.json');
```

---

## 5. Master Asset Registry (`registry.json`)

The central catalog at `assets/models/registry.json` indexes all library models with:
- Unique `id` and descriptive metadata.
- JSON parameter schemas with types, defaults, and bounds.
- Material shader profiles and color signatures.
- Pedagogical STEM tags for automated scene blueprint compilers.
- REST / GraphQL endpoint specifications for SaaS cloud integration.
