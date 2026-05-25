import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import Home from "@/pages/home";
import RepoOverview from "@/pages/repo-overview";
import Commits from "@/pages/commits";
import CommitDetail from "@/pages/commit-detail";
import Hotspots from "@/pages/hotspots";
import Insights from "@/pages/insights";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/repos/:repoId" component={RepoOverview} />
      <Route path="/repos/:repoId/commits" component={Commits} />
      <Route path="/repos/:repoId/commits/:sha" component={CommitDetail} />
      <Route path="/repos/:repoId/hotspots" component={Hotspots} />
      <Route path="/repos/:repoId/insights" component={Insights} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
