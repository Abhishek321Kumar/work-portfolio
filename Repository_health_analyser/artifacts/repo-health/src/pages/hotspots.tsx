import { useParams } from "wouter";
import { useGetRepo, useGetHotspots } from "@workspace/api-client-react";
import { Layout } from "@/components/layout";
import { Card } from "@/components/ui/card";
import { Flame } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

// Interpolate a risk score [0,1] to an HSL colour: green → yellow → red
function riskToHsl(risk: number) {
  const hue = Math.round((1 - risk) * 120); // 120=green, 0=red
  const sat = 70 + Math.round(risk * 20);
  const lum = 35 + Math.round((1 - risk) * 15);
  return `hsl(${hue}, ${sat}%, ${lum}%)`;
}

function baseName(path: string) {
  return path.split("/").pop() ?? path;
}

export default function Hotspots() {
  const { repoId } = useParams<{ repoId: string }>();
  const id = Number(repoId);

  const repo = useGetRepo(id);
  const hotspots = useGetHotspots(id);

  const files = hotspots.data ?? [];
  const maxRisk = Math.max(...files.map((f) => f.riskScore), 0.01);

  return (
    <Layout repoId={id} repoName={repo.data?.name}>
      <div className="px-6 py-6 max-w-5xl">
        <div className="mb-5">
          <h1 className="text-base font-semibold tracking-tight flex items-center gap-2">
            <Flame className="w-4 h-4 text-chart-2" />
            Hotspot Risk Map
          </h1>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Files coloured by composite risk score: churn × coupling × complexity.
            Redder = higher risk.
          </p>
        </div>

        {hotspots.isLoading ? (
          <div className="grid grid-cols-6 gap-1.5 mb-6">
            {Array.from({ length: 30 }).map((_, i) => (
              <div key={i} className="h-16 bg-card animate-pulse rounded border border-border" />
            ))}
          </div>
        ) : files.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground text-sm">No hotspot data yet.</div>
        ) : (
          <>
            {/* Heatmap grid */}
            <div className="grid grid-cols-4 sm:grid-cols-6 lg:grid-cols-8 gap-1.5 mb-6">
              {files.map((f, i) => {
                const norm = f.riskScore / maxRisk;
                const color = riskToHsl(norm);
                return (
                  <Tooltip key={f.filePath}>
                    <TooltipTrigger asChild>
                      <div
                        data-testid={`cell-hotspot-${i}`}
                        className="h-16 rounded flex flex-col items-center justify-center px-1 cursor-default transition-transform hover:scale-105"
                        style={{ background: color + "33", border: `1px solid ${color}66` }}
                      >
                        <span
                          className="text-[9px] font-medium text-center leading-tight break-all line-clamp-3 w-full"
                          style={{ color }}
                        >
                          {baseName(f.filePath)}
                        </span>
                        <span className="text-[9px] mt-1" style={{ color }}>
                          {(f.riskScore * 100).toFixed(0)}
                        </span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent
                      className="bg-card border-card-border text-xs p-3 max-w-[260px]"
                      side="top"
                    >
                      <p className="font-mono text-foreground mb-1 break-all">{f.filePath}</p>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[10px] text-muted-foreground">
                        <span>Risk score</span>
                        <span className="font-mono text-right" style={{ color }}>{(f.riskScore * 100).toFixed(1)}</span>
                        <span>Churn count</span>
                        <span className="font-mono text-right">{f.churnCount}</span>
                        <span>Coupling</span>
                        <span className="font-mono text-right">{f.couplingScore.toFixed(2)}</span>
                        <span>Complexity</span>
                        <span className="font-mono text-right">{f.complexityScore.toFixed(2)}</span>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                );
              })}
            </div>

            {/* Ranked list */}
            <Card className="p-4 bg-card border-card-border">
              <h2 className="text-xs font-semibold mb-3 text-foreground">Ranked Risk Files</h2>
              <div className="border border-border rounded overflow-hidden">
                <div className="grid grid-cols-[28px_1fr_72px_72px_72px_72px] gap-2 px-3 py-2 bg-muted/30 border-b border-border text-[10px] text-muted-foreground uppercase tracking-wider font-medium">
                  <span>#</span>
                  <span>File</span>
                  <span className="text-right">Risk</span>
                  <span className="text-right">Churn</span>
                  <span className="text-right">Coupling</span>
                  <span className="text-right">Complexity</span>
                </div>
                {files.map((f, i) => {
                  const norm = f.riskScore / maxRisk;
                  const color = riskToHsl(norm);
                  return (
                    <div
                      key={f.filePath}
                      data-testid={`row-hotspot-${i}`}
                      className="grid grid-cols-[28px_1fr_72px_72px_72px_72px] gap-2 px-3 py-1.5 border-b border-border last:border-b-0 hover:bg-muted/10 transition-colors text-xs"
                    >
                      <span className="text-muted-foreground text-[10px] tabular-nums">{i + 1}</span>
                      <span className="font-mono text-foreground truncate text-[11px]" title={f.filePath}>
                        {f.filePath}
                      </span>
                      <div className="text-right">
                        <span className="font-mono tabular-nums font-semibold" style={{ color }}>
                          {(f.riskScore * 100).toFixed(1)}
                        </span>
                      </div>
                      <span className="text-right font-mono tabular-nums text-muted-foreground">{f.churnCount}</span>
                      <span className="text-right font-mono tabular-nums text-muted-foreground">{f.couplingScore.toFixed(2)}</span>
                      <span className="text-right font-mono tabular-nums text-muted-foreground">{f.complexityScore.toFixed(2)}</span>
                    </div>
                  );
                })}
              </div>
            </Card>
          </>
        )}
      </div>
    </Layout>
  );
}
