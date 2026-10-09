import type { GraphNode } from "@/lib/warroom";
export function AgentGraph({ nodes }: { nodes: GraphNode[] }) {
  return (
    <ol className="agent-graph" aria-label="Actual pipeline stage states">
      {nodes.map((node, index) => (
        <li key={node.id} data-state={node.status}>
          <span className="graph-number">
            {String(index + 1).padStart(2, "0")}
          </span>
          <strong>{node.id}</strong>
          <span className="graph-state">
            {node.status.replaceAll("_", " ")}
          </span>
        </li>
      ))}
    </ol>
  );
}
