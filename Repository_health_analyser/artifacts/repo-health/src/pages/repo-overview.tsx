import { useParams } from "wouter";
import {
  useGetRepo, useGetRepoStats, useGetTimeline, useGetRiskiestFiles,
  getGetTimelineQueryKey, getGetRepoQueryKey, getGetRepoStatsQueryKey,
} from "@workspace/api-client-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { Layout } from "@/components/layout";
import { Card } from "@/components/ui/card";
import { Activity, GitCommit, Zap, AlertTriangle, FileText, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { Link } from "wouter";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  sub?: string;
  accent?: boolean;
}

function StatCard({ label, value, icon, sub, accent }: StatCardProps) {
  return (
    <Card className={cn("p-4 bg-card border-card-border", accent && "border-primary/40")}>
      <div className="flex items-start justify-between mb-2">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">{label}</span>
        <span className={cn("text-muted-foreground", accent && "text-primary")}>{icon}</span>
      </div>
      <div className={cn("text-2xl font-bold font-mono tabular-nums", accent && "text-primary")}>
        {value}
      </div>
      {sub && <p className="text-[10px] text-muted-foreground mt-0.5 truncate">{sub}</p>}
    </Card>
  );
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="bg-card border border-card-border rounded p-2.5 text-xs shadow-lg max-w-[200px]">
      <p className="font-mono text-muted-foreground mb-1">{d?.shortSha}</p>
      <p className="text-foreground truncate mb-1.5">{d?.message}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex justify-between gap-3">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="font-mono tabular-nums">{typeof p.value === "number" ? p.value.toFixed(2) : p.value}</span>
        </div>
      ))}
      {d?.isSpikeCommit && (
        <p className="text-chart-2 text-[10px] mt-1.5 flex items-center gap-1">
          <Zap className="w-2.5 h-2.5" /> Complexity spike
        </p>
      )}
    </div>
  );
};

export default function RepoOverview() {
  const { repoId } = useParams<{ repoId: string }>();
  const id = Number(repoId);

  const repo = useGetRepo(id, {
    query: {
      queryKey: getGetRepoQueryKey(id),
      refetchInterval: (query) => {
        const data = query.state.data;
        if (data && ["pending", "ingesting"].includes((data as any).status)) return 3000;
        return false;
      },
    },
  });
  const stats = useGetRepoStats(id, {
    query: {
      queryKey: getGetRepoStatsQueryKey(id),
      refetchInterval: (query) => {
        const repoStatus = repo.data?.status;
        if (repoStatus && ["pending", "ingesting"].includes(repoStatus)) return 4000;
        return false;
      },
    },
  });
  const timeline = useGetTimeline(id, {
    query: { queryKey: getGetTimelineQueryKey(id), enabled: !!id },
  });
  const riskiest = useGetRiskiestFiles(id);

  const timelineData = timeline.data ?? [];
  const statsData = stats.data;

  return (
    <Layout repoId={id} repoName={repo.data?.name}>
      <div className="px-6 py-6 max-w-5xl">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-base font-semibold tracking-tight flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            {repo.data?.name ?? "Loading…"}
          </h1>
          <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
            {repo.data?.url}
          </p>
        </div>

        {/* Stat cards */}
        {stats.isLoading ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 rounded bg-card animate-pulse border border-border" />
            ))}
          </div>
        ) : statsData ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            <StatCard
              label="Commits"
              value={statsData.analyzedCommits}
              icon={<GitCommit className="w-4 h-4" />}
              sub={`of ${statsData.totalCommits} total`}
            />
            <StatCard
              label="Avg Complexity"
              value={statsData.avgComplexity.toFixed(1)}
              icon={<TrendingUp className="w-4 h-4" />}
              sub={`max ${statsData.maxComplexity.toFixed(1)}`}
            />
            <StatCard
              label="Spikes"
              value={statsData.spikeCount}
              icon={<Zap className="w-4 h-4" />}
              sub="complexity anomalies"
              accent={statsData.spikeCount > 0}
            />
            <StatCard
              label="Files"
              value={statsData.totalFiles}
              icon={<FileText className="w-4 h-4" />}
              sub={statsData.mostChangedFile?.split("/").pop()}
            />
          </div>
        ) : null}

        {/* Health timeline */}
        <Card className="p-4 bg-card border-card-border mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-semibold text-foreground">Health Timeline</h2>
            <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-chart-1 inline-block" /> Complexity</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-chart-4 inline-block" /> Coupling</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-chart-2 inline-block border-dashed" /> Spike</span>
            </div>
          </div>
          {timeline.isLoading ? (
            <div className="h-48 bg-muted/30 animate-pulse rounded" />
          ) : timelineData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-muted-foreground text-xs">
              No timeline data yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={timelineData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="commitIndex"
                  tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip content={<CustomTooltip />} />
                {/* Spike reference lines */}
                {timelineData
                  .filter((d) => d.isSpikeCommit)
                  .map((d) => (
                    <ReferenceLine
                      key={d.sha}
                      x={d.commitIndex}
                      stroke="hsl(var(--chart-2))"
                      strokeWidth={1}
                      strokeDasharray="2 3"
                      strokeOpacity={0.6}
                    />
                  ))}
                <Line
                  name="Complexity"
                  type="monotone"
                  dataKey="complexity"
                  stroke="hsl(var(--chart-1))"
                  strokeWidth={1.5}
                  dot={false}
                  activeDot={{ r: 3, fill: "hsl(var(--chart-1))" }}
                />
                <Line
                  name="Coupling"
                  type="monotone"
                  dataKey="coupling"
                  stroke="hsl(var(--chart-4))"
                  strokeWidth={1.5}
                  dot={false}
                  activeDot={{ r: 3, fill: "hsl(var(--chart-4))" }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Riskiest files */}
        <Card className="p-4 bg-card border-card-border">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-chart-4" />
              Top Risk Files
            </h2>
            <Link href={`/repos/${id}/hotspots`} className="text-[10px] text-primary hover:underline">
              View all
            </Link>
          </div>
          {riskiest.isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <div key={i} className="h-6 bg-muted/30 animate-pulse rounded" />)}
            </div>
          ) : (riskiest.data ?? []).length === 0 ? (
            <p className="text-xs text-muted-foreground">No file data yet.</p>
          ) : (
            <div className="space-y-1">
              {(riskiest.data ?? []).slice(0, 8).map((file, i) => (
                <div
                  key={file.filePath}
                  data-testid={`row-riskiest-${i}`}
                  className="flex items-center gap-3 py-1"
                >
                  <span className="text-[10px] text-muted-foreground w-4 text-right tabular-nums">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono truncate text-foreground">{file.filePath}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground flex-shrink-0">
                    <span>churn {file.churnCount}</span>
                    <div className="w-16 h-1 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.round(file.riskScore * 100)}%`,
                          background: `hsl(${Math.round((1 - file.riskScore) * 120)}, 80%, 50%)`,
                        }}
                      />
                    </div>
                    <span className="font-mono tabular-nums w-8 text-right">
                      {(file.riskScore * 100).toFixed(0)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </Layout>
  );
}
