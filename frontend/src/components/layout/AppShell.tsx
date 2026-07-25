import { Suspense } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { PageContainer } from "@/components/layout/PageContainer";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { ErrorBoundary } from "@/components/system/ErrorBoundary";
import { Loading } from "@/components/ui/Loading";

export function AppShell() {
  const location = useLocation();

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-y-auto">
          <PageContainer>
            <ErrorBoundary key={location.pathname}>
              <Suspense fallback={<Loading />}>
                <Outlet />
              </Suspense>
            </ErrorBoundary>
          </PageContainer>
        </main>
      </div>
    </div>
  );
}