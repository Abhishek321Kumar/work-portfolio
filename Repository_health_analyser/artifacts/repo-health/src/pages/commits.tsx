import { useParams, useLocation } from "wouter";
import { useGetRepo, useListCommits } from "@workspace/api-client-react";
import { Layout } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Zap, GitCommit, Plus, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

function riskColor(churnRisk: number | null | undefined) {
  if (!churnRisk) return "text-muted-foreground";
  if (churnRisk > 5) return "text-chart-2";
  if (churnRisk > 2) return "text-chart-4";
  return "text-chart-1";
}

export default function Commits() {
  const { repoId } = useParams<{ repoId: string }>();
  const id = Number(repoId);
  const [, setLocation] = useLocation();

  const repo = useGetRepo(id);
  const commits = useListCommits(id);

  const commitList = commits.data?.commits ?? [];

  return (
    <Layout repoId={id} repoName={repo.data?.name}>
      <div className="px-6 py-6 max-w-5xl">
        <div className="mb-5">
          <h1 className="text-base font-semibold tracking-tight flex items-center gap-2">
            <GitCommit className="w-4 h-4 text-primary" />
            Commits
          </h1>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            {commits.data?.total ?? 0} commits analysed. Spikes flagged in{" "}
            <span className="text-chart-2">red</span>.
          </p>
        </div>

        {commits.isLoading ? (
          <div className="space-y-1">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="h-10 bg-card animate-pulse rounded border border-border" />
            ))}
          </div>
        ) : (
          <div className="border border-border rounded overflow-hidden">
            {/* Table header */}
            <div className="grid grid-cols-[80px_1fr_80px_64px_64px_64px] gap-2 px-3 py-2 bg-muted/30 border-b border-border text-[10px] text-muted-foreground uppercase tracking-wider font-medium">
              <span>SHA</span>
              <span>Message / Author</span>
              <span className="text-right">Complexity</span>
              <span className="text-right">Coupling</span>
              <span className="text-right">Files</span>
              <span className="text-right">Risk</span>
            </div>

            {/* Rows */}
            {commitList.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground text-xs">No commits yet.</div>
            ) : (
              commitList.map((c) => (
                <div
                  key={c.sha}
                  data-testid={`row-commit-${c.shortSha}`}
                  className={cn(
                    "grid grid-cols-[80px_1fr_80px_64px_64px_64px] gap-2 px-3 py-2 border-b border-border last:border-b-0 cursor-pointer hover:bg-muted/20 transition-colors text-xs",
                    c.isSpikeCommit && "bg-chart-2/5 hover:bg-chart-2/10"
                  )}
                  onClick={() => setLocation(`/repos/${id}/commits/${c.sha}`)}
                >
                  {/* SHA */}
                  <div className="flex items-center gap-1.5">
                    {c.isSpikeCommit && (
                      <Zap
                        data-testid={`icon-spike-${c.shortSha}`}
                        className="w-3 h-3 text-chart-2 flex-shrink-0"
                      />
                    )}
                    <span className="font-mono text-[10px] text-primary">{c.shortSha}</span>
                  </div>

                  {/* Message */}
                  <div className="min-w-0">
                    <p className="truncate text-foreground">{c.message}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{c.author}</p>
                  </div>

                  {/* Complexity */}
                  <div className="text-right font-mono tabular-nums text-muted-foreground">
                    {c.complexity != null ? c.complexity.toFixed(1) : "—"}
                  </div>

                  {/* Coupling */}
                  <div className="text-right font-mono tabular-nums text-muted-foreground">
                    {c.coupling != null ? c.coupling.toFixed(1) : "—"}
                  </div>

                  {/* Files */}
                  <div className="text-right font-mono tabular-nums">
                    <span className="text-muted-foreground">{c.filesChanged ?? "—"}</span>
                  </div>

                  {/* Churn risk */}
                  <div className={cn("text-right font-mono tabular-nums", riskColor(c.churnRisk))}>
                    {c.churnRisk != null ? c.churnRisk.toFixed(1) : "—"}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
