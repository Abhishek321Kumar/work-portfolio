import { useParams } from "wouter";
import { useState, useEffect, useRef } from "react";
import {
  useGetRepo, useGetCommit, useGetGraphDiff, useGetSpikeExplanation,
  getGetGraphDiffQueryKey, getGetSpikeExplanationQueryKey,
} from "@workspace/api-client-react";
import { Layout } from "@/components/layout";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Zap, GitCommit, TrendingUp, TrendingDown, CheckCircle, HelpCircle, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Link } from "wouter";

// ---------------------------------------------------------------------------
// Graph diff visualiser — SVG force-directed layout
// ---------------------------------------------------------------------------

interface GraphNode {
  id: string;
  label: string;
  kind: string;
  complexity?: number | null;
  fanIn?: number | null;
  fanOut?: number | null;
  changeType: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface GraphEdge {
  source: string;
  target: string;
  kind: string;
  changeType: string;
}

const CHANGE_COLORS = {
  added: "#22d3ee",    // cyan
  removed: "#f43f5e",  // red
  changed: "#facc15",  // amber
  unchanged: "#4b5563", // gray
} as const;

function forceLayout(rawNodes: any[], rawEdges: any[], w: number, h: number): GraphNode[] {
  if (!rawNodes.length) return [];

  const nodes: GraphNode[] = rawNodes.map((n, i) => ({
    ...n,
    x: w / 2 + Math.cos((i / rawNodes.length) * Math.PI * 2) * w * 0.3,
    y: h / 2 + Math.sin((i / rawNodes.length) * Math.PI * 2) * h * 0.3,
    vx: 0,
    vy: 0,
  }));

  const indexMap = new Map(nodes.map((n, i) => [n.id, i]));

  for (let iter = 0; iter < 120; iter++) {
    const alpha = 0.3 * Math.pow(0.95, iter);

    // Repulsion
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const d2 = dx * dx + dy * dy + 1;
        const f = (3000 / d2) * alpha;
        nodes[i].vx += dx * f;
        nodes[i].vy += dy * f;
        nodes[j].vx -= dx * f;
        nodes[j].vy -= dy * f;
      }
    }

    // Attraction (edges)
    rawEdges.forEach((e: GraphEdge) => {
      const si = indexMap.get(e.source);
      const ti = indexMap.get(e.target);
      if (si == null || ti == null) return;
      const dx = nodes[ti].x - nodes[si].x;
      const dy = nodes[ti].y - nodes[si].y;
      const d = Math.sqrt(dx * dx + dy * dy) + 0.01;
      const f = (d - 80) * 0.05 * alpha;
      nodes[si].vx += (dx / d) * f;
      nodes[si].vy += (dy / d) * f;
      nodes[ti].vx -= (dx / d) * f;
      nodes[ti].vy -= (dy / d) * f;
    });

    // Centre gravity
    nodes.forEach((n) => {
      n.vx += (w / 2 - n.x) * 0.01 * alpha;
      n.vy += (h / 2 - n.y) * 0.01 * alpha;
    });

    // Integrate
    nodes.forEach((n) => {
      n.x = Math.max(20, Math.min(w - 20, n.x + n.vx));
      n.y = Math.max(20, Math.min(h - 20, n.y + n.vy));
      n.vx *= 0.6;
      n.vy *= 0.6;
    });
  }

  return nodes;
}

function GraphDiffViz({ nodes: rawNodes, edges: rawEdges }: { nodes: any[]; edges: any[] }) {
  const W = 620, H = 340;
  const positions = forceLayout(rawNodes.slice(0, 60), rawEdges, W, H);
  const posMap = new Map(positions.map((n) => [n.id, { x: n.x, y: n.y }]));

  if (!positions.length) {
    return (
      <div className="h-48 flex items-center justify-center text-muted-foreground text-xs">
        No graph data for this commit
      </div>
    );
  }

  return (
    <div className="overflow-auto rounded bg-muted/10 border border-border">
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="block">
        <defs>
          <marker id="arrow" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
            <path d="M0,0 L4,2 L0,4 Z" fill="#4b5563" fillOpacity={0.6} />
          </marker>
        </defs>
        {/* Edges */}
        {rawEdges.slice(0, 100).map((e, i) => {
          const s = posMap.get(e.source);
          const t = posMap.get(e.target);
          if (!s || !t) return null;
          return (
            <line
              key={i}
              x1={s.x} y1={s.y}
              x2={t.x} y2={t.y}
              stroke={CHANGE_COLORS[e.changeType as keyof typeof CHANGE_COLORS] ?? "#4b5563"}
              strokeWidth={1}
              strokeOpacity={0.5}
              markerEnd="url(#arrow)"
            />
          );
        })}

        {/* Nodes */}
        {positions.map((n) => {
          const color = CHANGE_COLORS[n.changeType as keyof typeof CHANGE_COLORS] ?? "#4b5563";
          const label = n.label.length > 14 ? n.label.slice(0, 12) + "…" : n.label;
          if (n.kind === "function") {
            return (
              <g key={n.id}>
                <circle cx={n.x} cy={n.y} r={7} fill={color} fillOpacity={0.85} />
                <text x={n.x} y={n.y + 16} textAnchor="middle" fontSize={8} fill={color} fillOpacity={0.8}>{label}</text>
              </g>
            );
          }
          if (n.kind === "class") {
            return (
              <g key={n.id}>
                <polygon
                  points={`${n.x},${n.y - 8} ${n.x + 8},${n.y} ${n.x},${n.y + 8} ${n.x - 8},${n.y}`}
                  fill={color} fillOpacity={0.85}
                />
                <text x={n.x} y={n.y + 18} textAnchor="middle" fontSize={8} fill={color} fillOpacity={0.8}>{label}</text>
              </g>
            );
          }
          // file = rect
          return (
            <g key={n.id}>
              <rect x={n.x - 22} y={n.y - 7} width={44} height={14} rx={2}
                fill={color} fillOpacity={0.2} stroke={color} strokeWidth={1} />
              <text x={n.x} y={n.y + 4} textAnchor="middle" fontSize={7.5} fill={color}>{label}</text>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-4 px-3 pb-2 pt-1 text-[10px] text-muted-foreground flex-wrap">
        {(Object.entries(CHANGE_COLORS) as [string, string][]).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: c }} />
            {k}
          </span>
        ))}
        <span className="flex items-center gap-1"><span className="w-4 h-0 border-t border-muted-foreground inline-block" />file</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full border border-muted-foreground inline-block" />function</span>
        <span className="flex items-center gap-1">◆ class</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Delta badge
// ---------------------------------------------------------------------------
function DeltaBadge({ delta }: { delta: number | null | undefined }) {
  if (delta == null) return <span className="text-muted-foreground text-xs">—</span>;
  const pct = (delta * 100).toFixed(1);
  const up = delta > 0;
  return (
    <span className={cn("text-xs font-mono flex items-center gap-0.5", up ? "text-chart-2" : "text-chart-1")}>
      {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      {up ? "+" : ""}{pct}%
    </span>
  );
}

// ---------------------------------------------------------------------------
// Spike explanation panel
// ---------------------------------------------------------------------------
function SpikeExplanationPanel({ repoId, sha }: { repoId: number; sha: string }) {
  const [enabled, setEnabled] = useState(false);

  const explanation = useGetSpikeExplanation(repoId, sha, {
    query: {
      queryKey: getGetSpikeExplanationQueryKey(repoId, sha),
      enabled,
      retry: false,
    },
  });

  return (
    <Card className="p-4 bg-card border-chart-2/30 border mb-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 text-chart-2" />
          <h2 className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
            Spike Explanation
          </h2>
          {explanation.data?.cached && (
            <Badge variant="outline" className="text-[10px] h-4 border-muted-foreground/30 text-muted-foreground">
              cached
            </Badge>
          )}
        </div>
        {!enabled && !explanation.data && (
          <Button
            size="sm"
            variant="outline"
            className="h-6 text-[10px] px-2.5 border-chart-2/40 text-chart-2 hover:bg-chart-2/10"
            onClick={() => setEnabled(true)}
          >
            <Zap className="w-3 h-3 mr-1" />
            Explain Spike
          </Button>
        )}
      </div>

      {!enabled && !explanation.data ? (
        <p className="text-xs text-muted-foreground">
          This commit triggered a complexity spike (&gt;25% increase). Click "Explain Spike" to get an LLM analysis of what structural decision caused it.
        </p>
      ) : explanation.isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-3.5 bg-muted/40 animate-pulse rounded" style={{ width: `${70 + i * 10}%` }} />
          ))}
        </div>
      ) : explanation.data ? (
        <div className="space-y-3">
          {/* Explanation */}
          <p className="text-sm text-foreground leading-relaxed">
            {explanation.data.explanation}
          </p>

          {/* Intentional badge */}
          {explanation.data.isIntentional != null && (
            <div className="flex items-center gap-2">
              {explanation.data.isIntentional ? (
                <Badge variant="outline" className="text-[10px] h-5 border-chart-1/40 text-chart-1 flex items-center gap-1">
                  <CheckCircle className="w-2.5 h-2.5" />
                  Intentional change
                </Badge>
              ) : (
                <Badge variant="outline" className="text-[10px] h-5 border-chart-2/40 text-chart-2 flex items-center gap-1">
                  <AlertTriangle className="w-2.5 h-2.5" />
                  Accidental / needs review
                </Badge>
              )}
            </div>
          )}

          {/* Complexity stats */}
          {explanation.data.complexityBefore != null && (
            <div className="flex items-center gap-4 text-[10px] text-muted-foreground font-mono">
              <span>Before: <span className="text-foreground">{explanation.data.complexityBefore?.toFixed(2)}</span></span>
              <span>After: <span className="text-chart-2">{explanation.data.complexityAfter?.toFixed(2)}</span></span>
              {explanation.data.percentChange != null && (
                <span className="text-chart-2">+{explanation.data.percentChange.toFixed(1)}%</span>
              )}
            </div>
          )}

          {/* Recommendations */}
          {explanation.data.recommendations?.length > 0 && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5">
                Recommendations
              </p>
              <ul className="space-y-1">
                {explanation.data.recommendations.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-foreground">
                    <span className="text-chart-2 mt-0.5 flex-shrink-0">→</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : explanation.isError ? (
        <p className="text-xs text-destructive">
          Failed to generate explanation. Check that OPENAI_API_KEY is set, or try again.
        </p>
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function CommitDetail() {
  const { repoId, sha } = useParams<{ repoId: string; sha: string }>();
  const id = Number(repoId);

  const repo = useGetRepo(id);
  const commit = useGetCommit(id, sha);
  const graphDiff = useGetGraphDiff(id, sha, {
    query: { queryKey: getGetGraphDiffQueryKey(id, sha), enabled: !!sha },
  });

  const c = commit.data;

  return (
    <Layout repoId={id} repoName={repo.data?.name}>
      <div className="px-6 py-6 max-w-5xl">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-1 text-[11px] text-muted-foreground">
            <Link href={`/repos/${id}/commits`} className="hover:text-primary">
              Commits
            </Link>
            <span>/</span>
            <span className="font-mono">{sha.slice(0, 8)}</span>
            {c?.isSpikeCommit && (
              <Badge variant="destructive" className="text-[10px] h-4 px-1.5 flex items-center gap-0.5">
                <Zap className="w-2.5 h-2.5" /> Spike
              </Badge>
            )}
          </div>
          {c && (
            <>
              <h1 className="text-sm font-semibold">{c.message}</h1>
              <p className="text-[11px] text-muted-foreground mt-0.5">{c.author}</p>
            </>
          )}
        </div>

        {/* Spike explanation (only for spike commits) */}
        {c?.isSpikeCommit && <SpikeExplanationPanel repoId={id} sha={sha} />}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-5">
          {/* Metric deltas */}
          <Card className="p-4 bg-card border-card-border col-span-1">
            <h2 className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-3">Metric Deltas</h2>
            {commit.isLoading ? (
              <div className="space-y-2">{[1, 2, 3, 4].map((i) => <div key={i} className="h-5 bg-muted/30 animate-pulse rounded" />)}</div>
            ) : c ? (
              <div className="space-y-2.5">
                {[
                  { label: "Complexity", value: c.complexity?.toFixed(2), delta: c.complexityDelta },
                  { label: "Coupling", value: c.coupling?.toFixed(2), delta: c.couplingDelta },
                  { label: "Files Changed", value: c.filesChanged },
                  { label: "Lines +/-", value: `+${c.linesAdded ?? 0} / -${c.linesRemoved ?? 0}` },
                ].map(({ label, value, delta }) => (
                  <div key={label} className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{label}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono tabular-nums">{value ?? "—"}</span>
                      {"delta" in { delta } && <DeltaBadge delta={delta as number | null | undefined} />}
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </Card>

          {/* Changed files */}
          <Card className="p-4 bg-card border-card-border col-span-2">
            <h2 className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-3">Changed Files</h2>
            {commit.isLoading ? (
              <div className="space-y-1">{[1, 2, 3].map((i) => <div key={i} className="h-4 bg-muted/30 animate-pulse rounded" />)}</div>
            ) : (
              <div className="space-y-0.5 max-h-40 overflow-y-auto">
                {(c?.changedFiles ?? []).slice(0, 30).map((file) => (
                  <div key={file} className="text-[11px] font-mono text-muted-foreground hover:text-foreground py-0.5 truncate">
                    {file}
                  </div>
                ))}
                {(c?.changedFiles?.length ?? 0) === 0 && (
                  <p className="text-xs text-muted-foreground">No file data</p>
                )}
              </div>
            )}
          </Card>
        </div>

        {/* Top complex functions */}
        {(c?.topComplexFunctions?.length ?? 0) > 0 && (
          <Card className="p-4 bg-card border-card-border mb-5">
            <h2 className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-3">Top Complex Functions</h2>
            <div className="space-y-1.5">
              {c!.topComplexFunctions.map((fn, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-[10px] text-muted-foreground w-4 text-right">{i + 1}</span>
                  <span className="text-xs font-mono text-foreground flex-1 truncate">{fn.name}</span>
                  <span className="text-[10px] text-muted-foreground truncate max-w-[180px]">{fn.file}</span>
                  <span
                    className={cn("text-xs font-mono tabular-nums font-semibold",
                      fn.complexity > 10 ? "text-chart-2" : fn.complexity > 5 ? "text-chart-4" : "text-chart-1"
                    )}
                  >
                    {fn.complexity.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Graph diff */}
        <Card className="p-4 bg-card border-card-border">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
              Knowledge Graph Diff
            </h2>
            {graphDiff.data && (
              <div className="flex items-center gap-3 text-[10px]">
                <span className="text-chart-1">+{graphDiff.data.addedNodes} nodes</span>
                <span className="text-chart-2">-{graphDiff.data.removedNodes} nodes</span>
                <span className="text-muted-foreground">{graphDiff.data.addedEdges} new edges</span>
              </div>
            )}
          </div>
          {graphDiff.isLoading ? (
            <div className="h-48 bg-muted/20 animate-pulse rounded" />
          ) : graphDiff.data ? (
            <GraphDiffViz nodes={graphDiff.data.nodes} edges={graphDiff.data.edges} />
          ) : (
            <div className="h-32 flex items-center justify-center text-muted-foreground text-xs">
              No graph data available
            </div>
          )}
        </Card>
      </div>
    </Layout>
  );
}
