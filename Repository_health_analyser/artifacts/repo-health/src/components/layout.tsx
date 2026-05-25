import { Link, useLocation } from "wouter";
import { Activity, GitCommit, Flame, Lightbulb, Home, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface LayoutProps {
  children: React.ReactNode;
  repoId?: number;
  repoName?: string;
}

const NAV = [
  { label: "Repos", path: "/", icon: Home },
];

const REPO_NAV = [
  { label: "Overview", path: "", icon: Activity },
  { label: "Commits", path: "/commits", icon: GitCommit },
  { label: "Hotspots", path: "/hotspots", icon: Flame },
  { label: "Insights", path: "/insights", icon: Lightbulb },
];

export function Layout({ children, repoId, repoName }: LayoutProps) {
  const [location] = useLocation();

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Sidebar */}
      <aside className="w-52 flex-shrink-0 flex flex-col border-r border-border bg-sidebar">
        {/* Logo */}
        <div className="px-4 py-4 border-b border-sidebar-border">
          <Link
            href="/"
            className="flex items-center gap-2 cursor-pointer"
          >
            <Activity className="w-5 h-5 text-primary" />
            <span className="text-sm font-semibold tracking-tight text-sidebar-foreground">
              RepoHealth
            </span>
          </Link>
        </div>

        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          {/* Top-level nav */}
          {NAV.map(({ label, path, icon: Icon }) => (
            <Link
              key={path}
              href={path}
              data-testid={`nav-${label.toLowerCase()}`}
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-colors",
                location === path
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/60"
              )}
            >
              <Icon className="w-3.5 h-3.5 flex-shrink-0" />
              {label}
            </Link>
          ))}

          {/* Repo-specific nav */}
          {repoId && (
            <>
              <div className="pt-4 pb-1 px-3">
                <div className="flex items-center gap-1 text-[10px] text-muted-foreground uppercase tracking-wider font-medium">
                  <ChevronRight className="w-3 h-3" />
                  <span className="truncate max-w-[120px]" title={repoName}>
                    {repoName || `Repo #${repoId}`}
                  </span>
                </div>
              </div>
              {REPO_NAV.map(({ label, path, icon: Icon }) => {
                const href = `/repos/${repoId}${path}`;
                const isActive =
                  path === ""
                    ? location === href
                    : location.startsWith(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    data-testid={`nav-repo-${label.toLowerCase()}`}
                    className={cn(
                      "flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-colors",
                      isActive
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground hover:bg-sidebar-accent/60"
                    )}
                  >
                    <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                    {label}
                  </Link>
                );
              })}
            </>
          )}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-sidebar-border text-[10px] text-muted-foreground">
          codebase observatory
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
