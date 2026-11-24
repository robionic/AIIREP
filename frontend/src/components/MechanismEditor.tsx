"use client";

import { addEdge, Background, Controls, Edge, MarkerType, Node, ReactFlow, useEdgesState, useNodesState } from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import { api, Asset } from "@/lib/api";

type Props = { asset: Asset; onSaved: () => void };

export default function MechanismEditor({ asset, onSaved }: Props) {
  const graph = asset.mechanism_graph;
  const initialNodes = useMemo<Node[]>(() => (graph?.nodes ?? []).map((node, index) => ({
    id: node.id,
    position: { x: 70 + (index % 3) * 190, y: 55 + Math.floor(index / 3) * 120 },
    data: { label: node.label },
    style: { background: "#14251f", border: "1px solid #4f9277", color: "#e7f8ef", borderRadius: 8, padding: 10, width: 140 },
  })), [graph]);
  const initialEdges = useMemo<Edge[]>(() => (graph?.edges ?? []).map((edge, index) => ({
    id: `edge-${index}-${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    label: edge.label,
    markerEnd: { type: MarkerType.ArrowClosed, color: "#70d7b4" },
    style: { stroke: "#70d7b4" },
  })), [graph]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [status, setStatus] = useState("");

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  function addNode() {
    const id = `component-${Date.now()}`;
    setNodes((current) => [...current, {
      id,
      position: { x: 80 + (current.length % 3) * 190, y: 210 + Math.floor(current.length / 3) * 100 },
      data: { label: "New component" },
      style: { background: "#14251f", border: "1px solid #4f9277", color: "#e7f8ef", borderRadius: 8, padding: 10, width: 140 },
    }]);
  }

  async function save() {
    try {
      const graphNodes = nodes.map((node) => ({ id: node.id, label: String(node.data.label) }));
      const graphEdges = edges.map(({ source, target, label }) => ({ source, target, label: String(label ?? "") }));
      await api(`/api/assets/${asset.id}/mechanism?actor=${encodeURIComponent("Engineering reviewer")}`, {
        method: "PUT",
        body: JSON.stringify({ nodes: graphNodes, edges: graphEdges }),
      });
      setStatus("Mechanism graph saved as a new review revision.");
      onSaved();
    } catch (reason) {
      setStatus(reason instanceof Error ? reason.message : "Could not save graph.");
    }
  }

  return (
    <div>
      <div className="toolbar" style={{ marginBottom: 10 }}>
        <button className="button secondary" onClick={addNode}>Add node</button>
        <span className="muted small">Drag nodes and connect handles to edit relationships.</span>
        <button className="button" onClick={save}>Save graph</button>
      </div>
      <div className="graph-canvas">
        <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          onConnect={(connection) => setEdges((current) => addEdge({ ...connection, markerEnd: { type: MarkerType.ArrowClosed, color: "#70d7b4" }, style: { stroke: "#70d7b4" } }, current))}
          fitView>
          <Background color="#293b49" gap={20} /><Controls />
        </ReactFlow>
      </div>
      {status && <div className="muted small" style={{ marginTop: 8 }}>{status}</div>}
    </div>
  );
}
