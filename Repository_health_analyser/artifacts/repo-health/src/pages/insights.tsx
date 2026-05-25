import { useParams } from "wouter";
import {
  useGetRepo, useGetArchitecturalSummary, useGetRepoNarrative,
  getGetArchitecturalSummaryQueryKey, getGetRepoNarrativeQueryKey,
} from "@workspace/api-client-react";
import { Layout } from "@/components/layout";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Lightbulb, BookOpen, AlertTriangle, TrendingUp, Sparkles, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

function Section({
  icon,
  title,
  badge,
  children,
  isLoading,
}: {
  icon: React.ReactNode;
  title: string;
  badge?: string;
  children: React.ReactNode;
  isLoading?: boolean;
}) {
  return (
    <Card className="p-5 bg-card border-card-border">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xs font-semibold flex items-center gap-2 text-foreground">
          {icon}
          {title}
        </h2>
        {badge && (
          <Badge variant="outline" className="text-[10px] h-5 text-primary border-primary/30">
            {badge}
          </Badge>
        )}
      </div>
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-4 bg-muted/30 animate-pulse rounded" />
          ))}
        </div>
      ) : (
        children
      )}
    </Card>
  );
}

export default function Insights() {
  const { repoId } = useParams<{ repoId: string }>();
  const id = Number(repoId);

  const repo = useGetRepo(id);
  const summary = useGetArchitecturalSummary(id, {
    query: {
      queryKey: getGetArchitecturalSummaryQueryKey(id),
      enabled: !!id,
    },
  });
  const narrative = useGetRepoNarrative(id, {
    query: {
      queryKey: getGetRepoNarrativeQueryKey(id),
      enabled: !!id,
    },
  });

  const summaryData = summary.data;
  const narrativeData = narrative.data;

  return (
    <Layout repoId={id} repoName={repo.data?.name}>
      <div className="px-6 py-6 max-w-3xl">
        <div className="mb-6">
          <h1 className="text-base font-semibold tracking-tight flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-primary" />
            LLM Insights
          </h1>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            AI-powered analysis of architectural drift, spike patterns, and health trajectory.
            Responses are cached after first generation.
          </p>
        </div>

        <div className="space-y-4">
          {/* Architectural summary */}
          <Section
            icon={<TrendingUp className="w-3.5 h-3.5 text-chart-4" />}
            title="Architectural Drift Summary"
            badge={summaryData?.cached ? "Cached" : undefined}
            isLoading={summary.isLoading}
          >
            {summaryData ? (
              <>
                <p
                  data-testid="text-arch-summary"
                  className="text-sm text-foreground leading-relaxed mb-4"
                >
                  {summaryData.summary}
                </p>

                {summaryData.keyTrends?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
                      Key Trends
                    </p>
                    <ul className="space-y-1.5">
                      {summaryData.keyTrends.map((trend, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs text-foreground">
                          <span className="text-primary mt-0.5 flex-shrink-0">→</span>
                          {trend}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {summaryData.riskModules?.length > 0 && (
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3 text-chart-2" />
                      Risk Modules
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {summaryData.riskModules.map((mod, i) => (
                        <Badge
                          key={i}
                          variant="outline"
                          className="text-[10px] font-mono border-chart-2/40 text-chart-2"
                        >
                          {mod}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {summaryData.generatedAt && (
                  <p className="text-[10px] text-muted-foreground mt-4">
                    Generated {new Date(summaryData.generatedAt).toLocaleString()}
                  </p>
                )}
              </>
            ) : (
              <p className="text-xs text-muted-foreground">
                {summary.error ? "Failed to load summary." : "No summary available yet."}
              </p>
            )}
          </Section>

          {/* Full narrative */}
          <Section
            icon={<BookOpen className="w-3.5 h-3.5 text-chart-1" />}
            title="Repository Health Narrative"
            badge={narrativeData?.cached ? "Cached" : undefined}
            isLoading={narrative.isLoading}
          >
            {narrativeData ? (
              <>
                <p
                  data-testid="text-narrative"
                  className="text-sm text-foreground leading-relaxed mb-4 prose prose-invert max-w-none"
                >
                  {narrativeData.narrative}
                </p>

                {narrativeData.highlights?.length > 0 && (
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2 flex items-center gap-1">
                      <Sparkles className="w-3 h-3 text-chart-1" />
                      Highlights
                    </p>
                    <ul className="space-y-1.5">
                      {narrativeData.highlights.map((h, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs text-foreground">
                          <span className="text-chart-1 mt-0.5 flex-shrink-0">•</span>
                          {h}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {narrativeData.generatedAt && (
                  <p className="text-[10px] text-muted-foreground mt-4">
                    Generated {new Date(narrativeData.generatedAt).toLocaleString()}
                  </p>
                )}
              </>
            ) : (
              <p className="text-xs text-muted-foreground">
                {narrative.error ? "Failed to load narrative." : "Narrative not yet generated."}
              </p>
            )}
          </Section>

          {/* Spike explanation notice */}
          <Card className="p-5 bg-card border-card-border">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-3.5 h-3.5 text-chart-2" />
              <h2 className="text-xs font-semibold text-foreground">Spike Explanations</h2>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Spike explanations are generated per-commit when you visit a commit flagged as a spike.
              Navigate to{" "}
              <span className="text-primary font-medium">Commits → [spike commit]</span>
              {" "}and click "Explain Spike" to trigger LLM analysis for that specific commit.
              Responses are cached after the first call.
            </p>
          </Card>
        </div>
      </div>
    </Layout>
  );
}

