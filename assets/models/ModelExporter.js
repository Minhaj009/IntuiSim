/**
 * IntuiSim Modular 3D Asset Library - ModelExporter.js
 * Browser & Headless GLTF / GLB / JSON Asset Serializer
 *
 * Enables future SaaS users to download any customized atom, orbital, or unit cell
 * as an industry-standard .glb asset or inspect procedural JSON hierarchy.
 */

import * as THREE from '../vendor/three.module.js';

export class ModelExporter {
  /**
   * Exports any Three.js Object3D / Group to a binary .glb file
   * @param {THREE.Object3D} object3d - Target 3D model
   * @param {string} [filename='model.glb'] - Download filename
   * @param {Object} [options={}] - GLTFExporter configuration options
   * @returns {Promise<ArrayBuffer>}
   */
  static async exportToGLB(object3d, filename = 'model.glb', options = {}) {
    if (!object3d) {
      throw new Error('[ModelExporter] Target Object3D cannot be null or undefined.');
    }

    const defaultOptions = {
      binary: true,
      embedImages: true,
      truncateDrawRange: true,
      maxTextureSize: 2048
    };
    const exportConfig = Object.assign(defaultOptions, options);

    // Dynamic import of GLTFExporter
    let GLTFExporterClass;
    if (typeof THREE.GLTFExporter !== 'undefined') {
      GLTFExporterClass = THREE.GLTFExporter;
    } else {
      try {
        const module = await import('../vendor/three/addons/exporters/GLTFExporter.js');
        GLTFExporterClass = module.GLTFExporter;
      } catch (err) {
        // Fallback to node_modules path if running in Vite / Node environment
        try {
          const nodeModule = await import('three/examples/jsm/exporters/GLTFExporter.js');
          GLTFExporterClass = nodeModule.GLTFExporter;
        } catch (nodeErr) {
          console.warn('[ModelExporter] GLTFExporter not found in vendor bundles. Falling back to JSON export.');
          return ModelExporter.exportToJSON(object3d, filename.replace(/\.glb$/, '.json'));
        }
      }
    }

    const exporter = new GLTFExporterClass();

    return new Promise((resolve, reject) => {
      exporter.parse(
        object3d,
        (result) => {
          if (exportConfig.binary) {
            const blob = new Blob([result], { type: 'model/gltf-binary' });
            ModelExporter.triggerBrowserDownload(blob, filename);
            resolve(result);
          } else {
            const output = JSON.stringify(result, null, 2);
            const blob = new Blob([output], { type: 'application/json' });
            ModelExporter.triggerBrowserDownload(blob, filename.replace(/\.glb$/, '.gltf'));
            resolve(result);
          }
        },
        (error) => {
          console.error('[ModelExporter] GLTF export error:', error);
          reject(error);
        },
        exportConfig
      );
    });
  }

  /**
   * Serializes a Three.js Object3D hierarchy to Three.js Object JSON
   * @param {THREE.Object3D} object3d
   * @param {string} [filename='model.json']
   * @returns {Object}
   */
  static exportToJSON(object3d, filename = 'model.json') {
    if (!object3d) {
      throw new Error('[ModelExporter] Target Object3D cannot be null or undefined.');
    }

    const json = object3d.toJSON();
    const str = JSON.stringify(json, null, 2);
    const blob = new Blob([str], { type: 'application/json' });
    ModelExporter.triggerBrowserDownload(blob, filename);
    return json;
  }

  /**
   * Triggers a client-side file download in browser environments
   * @param {Blob} blob - Data blob
   * @param {string} filename - Filename to save
   */
  static triggerBrowserDownload(blob, filename) {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      // Headless / Node environment: no browser DOM available
      return;
    }

    const link = document.createElement('a');
    link.style.display = 'none';
    link.href = URL.createObjectURL(blob);
    link.download = filename;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => {
      URL.revokeObjectURL(link.href);
    }, 1500);
  }
}
