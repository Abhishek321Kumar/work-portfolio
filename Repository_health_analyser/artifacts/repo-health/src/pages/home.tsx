import { useState } from "react";
import { useLocation } from "wouter";
import { useListRepos, useIngestRepo, useDeleteRepo, getListReposQueryKey, getGetRepoQueryKey } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Layout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Activity, GitBranch, Trash2, Plus, AlertCircle, Clock, CheckCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const STATUS_CONFIG = {
  pending: { label: "Queued", color: "text-muted-foreground", icon: Clock },
  ingesting: { label: "Ingesting", color: "text-chart-4", icon: Activity },
  ready: { label: "Ready", color: "text-chart-1", icon: CheckCircle },
  error: { label: "Error", color: "text-destructive", icon: AlertCircle },
} as const;

export default function Home() {
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const repos = useListRepos({
    query: {
      queryKey: getListReposQueryKey(),
      refetchInterval: (query) => {
        const data = query.state.data;
        if (Array.isArray(data) && data.some((r: any) => ["pending", "ingesting"].includes(r.status))) {
          return 3000;
        }
        return false;
      },
    },
  });
  const ingestRepo = useIngestRepo();
  const deleteRepo = useDeleteRepo();

  function handleIngest(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    ingestRepo.mutate(
      { data: { url: url.trim(), name: name.trim() || undefined, maxCommits: 300 } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getListReposQueryKey() });
          setUrl("");
          setName("");
          toast({ title: "Ingestion started", description: "Repository is being analysed in the background." });
        },
        onError: (err) => {
          toast({ title: "Failed", description: err.message, variant: "destructive" });
        },
      }
    );
  }

  function handleDelete(id: number, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("Delete this repository and all its data?")) return;
    deleteRepo.mutate(
      { repoId: id },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getListReposQueryKey() });
        },
      }
    );
  }

  const repoList = repos.data ?? [];

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-1">
            <Activity className="w-5 h-5 text-primary" />
            <h1 className="text-lg font-semibold tracking-tight">Repositories</h1>
          </div>
          <p className="text-xs text-muted-foreground">
            Ingest a public Git repository to start analysing code health over time.
          </p>
        </div>

        {/* Ingest form */}
        <Card className="p-4 mb-6 bg-card border-card-border">
          <form onSubmit={handleIngest} className="space-y-3">
            <div className="text-xs font-medium text-foreground mb-3 flex items-center gap-1.5">
              <Plus className="w-3.5 h-3.5 text-primary" />
              Ingest repository
            </div>
            <div className="flex gap-2">
              <Input
                data-testid="input-repo-url"
                className="flex-1 h-8 text-xs font-mono bg-background border-border"
                placeholder="https://github.com/user/repo"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
              <Input
                data-testid="input-repo-name"
                className="w-40 h-8 text-xs bg-background border-border"
                placeholder="Name (optional)"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <Button
                data-testid="button-ingest"
                type="submit"
                size="sm"
                className="h-8 text-xs px-4"
                disabled={!url.trim() || ingestRepo.isPending}
              >
                {ingestRepo.isPending ? "Starting…" : "Ingest"}
              </Button>
            </div>
            <p className="text-[10px] text-muted-foreground">
              Only public HTTPS repositories supported. Analyses up to 300 commits.
            </p>
          </form>
        </Card>

        {/* Repository list */}
        {repos.isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded bg-card animate-pulse border border-border" />
            ))}
          </div>
        ) : repoList.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <GitBranch className="w-8 h-8 mx-auto mb-3 opacity-40" />
            <p className="text-sm">No repositories yet. Ingest one above to begin.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {Array.isArray(repoList) && repoList.map((repo) => {
              const cfg = STATUS_CONFIG[repo.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.pending;
              const Icon = cfg.icon;
              const progress =
                repo.totalCommits && repo.processedCommits
                  ? Math.round((repo.processedCommits / repo.totalCommits) * 100)
                  : null;

              return (
                <Card
                  key={repo.id}
                  data-testid={`card-repo-${repo.id}`}
                  className={cn(
                    "px-4 py-3 bg-card border-card-border cursor-pointer hover:border-primary/40 transition-colors",
                    repo.status === "ready" && "cursor-pointer"
                  )}
                  onClick={() => repo.status === "ready" && setLocation(`/repos/${repo.id}`)}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span
                          data-testid={`text-repo-name-${repo.id}`}
                          className="text-sm font-medium truncate"
                        >
                          {repo.name}
                        </span>
                        <Icon className={cn("w-3.5 h-3.5 flex-shrink-0", cfg.color)} />
                        <span className={cn("text-[10px] font-medium", cfg.color)}>
                          {cfg.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-[10px] text-muted-foreground font-mono">
                        <span className="truncate max-w-xs">{repo.url}</span>
                        {repo.totalCommits && (
                          <span className="flex-shrink-0">{repo.totalCommits} commits</span>
                        )}
                      </div>
                      {/* Progress bar for ingesting */}
                      {repo.status === "ingesting" && progress !== null && (
                        <div className="mt-2">
                          <div className="h-0.5 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary rounded-full transition-all"
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                          <span className="text-[10px] text-muted-foreground mt-0.5 inline-block">
                            {repo.processedCommits}/{repo.totalCommits} commits
                          </span>
                        </div>
                      )}
                      {repo.status === "error" && repo.errorMessage && (
                        <p className="text-[10px] text-destructive mt-0.5 truncate">{repo.errorMessage}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      {repo.status === "ready" && (
                        <Badge
                          variant="outline"
                          className="text-[10px] h-5 border-primary/30 text-primary cursor-pointer"
                          onClick={() => setLocation(`/repos/${repo.id}`)}
                        >
                          View
                        </Badge>
                      )}
                      <button
                        data-testid={`button-delete-${repo.id}`}
                        className="text-muted-foreground hover:text-destructive transition-colors p-1"
                        onClick={(e) => handleDelete(repo.id, e)}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
}
