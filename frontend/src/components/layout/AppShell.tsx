import { Suspense } from "react";
import { Outlet } from "react-router-dom";

import { PageContainer } from "@/components/layout/PageContainer";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Loading } from "@/components/ui/Loading";

export function AppShell() {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-y-auto">
          <PageContainer>
            <Suspense fallback={<Loading />}>
              <Outlet />
            </Suspense>
          </PageContainer>
        </main>
      </div>
    </div>
  );
}