import {
  Background,
  type Edge,
  Handle,
  type Node,
  Position,
  ReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";

import type { GraphNodeName } from "../api/types";

interface GraphViewProps {
  currentNode: GraphNodeName | null;
  completedNodes: GraphNodeName[];
}

interface NodeData extends Record<string, unknown> {
  label: string;
  active: boolean;
  done: boolean;
}

function StepNode({ data }: { data: NodeData }) {
  const base = "rounded-lg border-2 px-3 py-2 text-sm font-medium shadow-sm min-w-[132px] text-center transition-colors";
  const cls = data.active
    ? `${base} border-brand-500 bg-brand-500 text-white animate-pulse`
    : data.done
      ? `${base} border-brand-300 bg-brand-50 text-brand-800`
      : `${base} border-slate-300 bg-white text-slate-500`;
  return (
    <div className={cls}>
      <Handle type="target" position={Position.Top} className="!bg-slate-400" />
      {data.label}
      <Handle type="source" position={Position.Bottom} className="!bg-slate-400" />
    </div>
  );
}

const nodeTypes = { step: StepNode };

const LAYOUT: Record<GraphNodeName, { x: number; y: number; label: string }> = {
  plan: { x: 260, y: 0, label: "1. Plan" },
  research: { x: 260, y: 100, label: "2. Research" },
  draft: { x: 260, y: 200, label: "3. Draft" },
  critique: { x: 260, y: 300, label: "4. Critique" },
  human_review: { x: 260, y: 420, label: "5. Human Review" },
  finalize: { x: 260, y: 520, label: "6. Finalize" },
};

export function GraphView({ currentNode, completedNodes }: GraphViewProps) {
  const nodes: Node[] = useMemo(
    () =>
      (Object.keys(LAYOUT) as GraphNodeName[]).map((id) => ({
        id,
        type: "step",
        position: { x: LAYOUT[id].x, y: LAYOUT[id].y },
        data: {
          label: LAYOUT[id].label,
          active: currentNode === id,
          done: completedNodes.includes(id) && currentNode !== id,
        } satisfies NodeData,
        draggable: false,
      })),
    [currentNode, completedNodes],
  );

  const edgeStyle = (active: boolean) => ({ stroke: active ? "#265ef2" : "#cbd5e1", strokeWidth: active ? 2.5 : 1.5 });

  const edges: Edge[] = useMemo(
    () => [
      { id: "e-plan-research", source: "plan", target: "research", style: edgeStyle(completedNodes.includes("research")) },
      { id: "e-research-draft", source: "research", target: "draft", style: edgeStyle(completedNodes.includes("draft")) },
      { id: "e-draft-critique", source: "draft", target: "critique", style: edgeStyle(completedNodes.includes("critique")) },
      {
        id: "e-critique-human",
        source: "critique",
        target: "human_review",
        label: "approve",
        style: edgeStyle(completedNodes.includes("human_review")),
      },
      {
        id: "e-critique-research",
        source: "critique",
        target: "research",
        label: "revise (loop)",
        type: "smoothstep",
        style: { stroke: "#f59e0b", strokeWidth: 1.5, strokeDasharray: "4 3" },
      },
      {
        id: "e-human-finalize",
        source: "human_review",
        target: "finalize",
        label: "approve / reject",
        style: edgeStyle(completedNodes.includes("finalize")),
      },
      {
        id: "e-human-research",
        source: "human_review",
        target: "research",
        label: "revise (loop)",
        type: "smoothstep",
        style: { stroke: "#f59e0b", strokeWidth: 1.5, strokeDasharray: "4 3" },
      },
    ],
    [completedNodes],
  );

  return (
    <div className="h-[560px] w-full rounded-xl border border-slate-200 bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <Background gap={16} color="#e2e8f0" />
      </ReactFlow>
    </div>
  );
}
