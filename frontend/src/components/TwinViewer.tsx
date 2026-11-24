"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useState } from "react";
import { Asset } from "@/lib/api";

function TwinScene({ asset }: { asset: Asset }) {
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <>
      <ambientLight intensity={1.2} />
      <directionalLight position={[4, 6, 4]} intensity={2} />
      <gridHelper args={[12, 12, "#314b5d", "#203441"]} position={[0, -1.1, 0]} />
      {asset.components.map((component, index) => (
        <mesh key={component.id} position={[(index - (asset.components.length - 1) / 2) * 1.6, 0, 0]} onClick={() => setSelected(component.id)}>
          {component.component_type.toLowerCase().includes("motor") ? <cylinderGeometry args={[0.52, 0.52, 1.1, 24]} /> : <boxGeometry args={[1.15, 0.72, 0.75]} />}
          <meshStandardMaterial color={selected === component.id ? "#f5c46b" : component.approved ? "#70d7b4" : "#5794b2"} wireframe={false} />
        </mesh>
      ))}
      <OrbitControls makeDefault />
    </>
  );
}

export default function TwinViewer({ asset }: { asset: Asset }) {
  const selected = asset.components[0];
  return (
    <div>
      <div className="viewer"><Canvas camera={{ position: [4, 3, 5], fov: 45 }}><TwinScene asset={asset} /></Canvas></div>
      <div className="muted small" style={{ marginTop: 8 }}>
        Schematic placeholder geometry for review visualization—not measured CAD geometry. Click and orbit to inspect.
        {selected && <> Selectable components: {asset.components.map((component) => component.name).join(", ") || "none detected"}.</>}
      </div>
    </div>
  );
}
