// Only the parts of three.js the Earth uses. Importing from three/src lets the
// bundler drop the rest of the library (loaders, extra materials, animation,
// audio and so on) that `import * from "three"` keeps. Loaded lazily by Earth.jsx.
export { WebGLRenderer } from "three/src/renderers/WebGLRenderer.js";
export { Scene } from "three/src/scenes/Scene.js";
export { PerspectiveCamera } from "three/src/cameras/PerspectiveCamera.js";
export { TextureLoader } from "three/src/loaders/TextureLoader.js";
export { DataTexture } from "three/src/textures/DataTexture.js";
export { Vector3 } from "three/src/math/Vector3.js";
export { Color } from "three/src/math/Color.js";
export { ShaderMaterial } from "three/src/materials/ShaderMaterial.js";
export { LineBasicMaterial } from "three/src/materials/LineBasicMaterial.js";
export { MeshBasicMaterial } from "three/src/materials/MeshBasicMaterial.js";
export { Group } from "three/src/objects/Group.js";
export { Mesh } from "three/src/objects/Mesh.js";
export { Line } from "three/src/objects/Line.js";
export { SphereGeometry } from "three/src/geometries/SphereGeometry.js";
export { BufferGeometry } from "three/src/core/BufferGeometry.js";
export {
  AdditiveBlending,
  ACESFilmicToneMapping,
  BackSide,
  SRGBColorSpace,
} from "three/src/constants.js";
