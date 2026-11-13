import { memo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  BaseEdge,
  getBezierPath,
  type Node,
  type NodeProps,
  type Edge,
  type EdgeProps,
  type ReactFlowInstance,
  MarkerType,
} from "@xyflow/react";
import { Sparkles, CircleCheck, Maximize2, Scan, Focus } from "lucide-react";
import "@xyflow/react/dist/style.css";

import { steps } from "./flowSteps";
export { steps } from "./flowSteps";

type FlowNode = Node<{ step: number }, "pipeline">;
const initial: FlowNode[] = steps.map((s, i) => ({
  id: s.id,
  type: "pipeline",
  position: { x: s.x, y: s.y },
  data: { step: i },
  selected: i === 1,
}));
function load() {
  try {
    const saved = JSON.parse(
      localStorage.getItem("cnooc-studio-layout") || "null",
    );
    if (
      saved &&
      initial.every(
        (n) =>
          Number.isFinite(saved[n.id]?.x) &&
          Number.isFinite(saved[n.id]?.y) &&
          Math.abs(saved[n.id].x) < 10000 &&
          Math.abs(saved[n.id].y) < 10000,
      )
    )
      return initial.map((n) => ({ ...n, position: saved[n.id] }));
  } catch {
    /* Storage is optional. */
  }
  return initial;
}
const PipelineNode = memo(({ data, selected }: NodeProps<FlowNode>) => {
  const step = steps[data.step],
    Icon = step.icon;
  return (
    <div
      className={`pipeline-node node-${step.color} ${selected ? "chosen" : ""}`}
    >
      <Handle type="target" position={Position.Left} />
      <div className="node-top">
        <span className={`icon-box ${step.color}`}>
          <Icon size={19} />
        </span>
        <strong>{step.title}</strong>
        <span className="node-number">0{data.step + 1}</span>
      </div>
      <div className="node-subtitle">{step.subtitle}</div>
      <div className="node-code">
        <span />
        {step.id}
        <span className="node-kind">{data.step === 5 ? "BRANCH" : "STEP"}</span>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
});
const nodeTypes = { pipeline: PipelineNode };
const colors: Record<string, string> = {
  retrieve: "#72a8ff",
  build_context: "#57d6c0",
  generate: "#b7a0ff",
  map_citations: "#57d6c0",
  no_evidence: "#e8b467",
};
const baseEdges: Edge[] = [
  ["check_index", "retrieve"],
  ["retrieve", "build_context"],
  ["build_context", "generate"],
  ["generate", "map_citations"],
  ["retrieve", "no_evidence"],
].map(([source, target]) => ({
  id: `${source}-${target}`,
  source,
  target,
  type: "signal",
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 14,
    height: 14,
    color: colors[target],
  },
  style: {
    stroke: colors[target],
    strokeWidth: 1.5,
    strokeDasharray: target === "no_evidence" ? "5 6" : undefined,
  },
}));
function SignalEdge(props: EdgeProps) {
  const [path] = getBezierPath(props);
  const color = String(props.style?.stroke || "#72a8ff");
  return (
    <>
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={9}
        opacity={0.035}
      />
      <BaseEdge
        id={props.id}
        path={path}
        style={{ ...props.style, opacity: 0.48 }}
        markerEnd={props.markerEnd}
      />
      {props.data?.animated && (
        <g className="edge-particles" aria-hidden="true">
          <circle r="3.1" fill={color} className="signal-halo">
            <animateMotion dur="5.5s" repeatCount="indefinite" path={path} />
          </circle>
          <circle r="1.4" fill="#edf9ff">
            <animateMotion dur="5.5s" repeatCount="indefinite" path={path} />
          </circle>
        </g>
      )}
    </>
  );
}
const edgeTypes = { signal: SignalEdge };
export default function Flow({
  onSelect,
  onNotice,
  animated,
  running,
}: {
  onSelect: (id: string) => void;
  onNotice: (s: string) => void;
  animated: boolean;
  running: boolean;
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState(load());
  const [instance, setInstance] = useState<ReactFlowInstance<FlowNode> | null>(
    null,
  );
  const [selected, setSelected] = useState("retrieve");
  const duration = animated ? 650 : 0;
  return (
    <div className={`flow-wrap ${running ? "request-pending" : ""}`}>
      <div className="canvas-atmosphere" aria-hidden="true">
        <span />
        <span />
      </div>
      <div className="canvas-label">
        <span className="tiny-dot" />
        QUERY PIPELINE<span>固定流程 · 滚轮缩放与拖动</span>
      </div>
      <div className="canvas-actions">
        <button
          title="显示全部节点"
          onClick={() => instance?.fitView({ padding: 0.15, duration })}
        >
          <Scan size={13} />
          总览
        </button>
        <button
          title="放大查看选中节点"
          onClick={() => {
            const node = nodes.find((n) => n.id === selected);
            if (node)
              void instance?.setCenter(
                node.position.x + 120,
                node.position.y + 70,
                { zoom: 0.95, duration },
              );
          }}
        >
          <Focus size={13} />
          聚焦
        </button>
        <button
          title="恢复默认节点布局"
          onClick={() => {
            setNodes(initial);
            setSelected("retrieve");
            onSelect("retrieve");
            void instance?.setViewport(
              { x: 25, y: 0, zoom: 0.85 },
              { duration },
            );
            onNotice("已恢复默认布局，保存后覆盖旧布局。");
          }}
        >
          <Maximize2 size={13} />
          重置
        </button>
        <button
          onClick={() => {
            try {
              localStorage.setItem(
                "cnooc-studio-layout",
                JSON.stringify(
                  Object.fromEntries(nodes.map((n) => [n.id, n.position])),
                ),
              );
              onNotice("布局已保存在此浏览器。");
            } catch {
              onNotice("浏览器存储不可用，布局未保存。");
            }
          }}
        >
          <CircleCheck size={13} />
          保存
        </button>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={baseEdges.map((e) => ({ ...e, data: { animated } }))}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onInit={setInstance}
        onNodesChange={onNodesChange}
        onNodeClick={(_, n) => {
          setSelected(n.id);
          onSelect(n.id);
        }}
        defaultViewport={{ x: 25, y: 0, zoom: 0.85 }}
        minZoom={0.25}
        maxZoom={1.5}
        colorMode="dark"
        nodesConnectable={false}
        edgesReconnectable={false}
        deleteKeyCode={null}
      >
        <Background color="#3b4b5f" gap={26} size={0.8} />
        <Controls showInteractive={false} />
        <MiniMap
          pannable
          zoomable
          nodeColor={(n) => colors[n.id] || "#b7a0ff"}
          maskColor="#080d16bb"
        />
      </ReactFlow>
      <div className="canvas-footer">
        <span className="visual-motion-badge">
          <Sparkles size={11} />
          {animated ? "视觉动效" : "静态视图"}
        </span>
        <span>连线流光不代表实时执行轨迹</span>
      </div>
      {running && (
        <div className="request-indicator">
          <span className="tiny-dot" />
          请求执行中 · 等待 API 返回
        </div>
      )}
    </div>
  );
}
