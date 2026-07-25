import type { ReactNode } from "react";

export interface PageContainerProps {
  children: ReactNode;
}

export function PageContainer({ children }: PageContainerProps) {
  return <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">{children}</div>;
}