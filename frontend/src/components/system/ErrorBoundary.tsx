import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

import { Button } from "@/components/ui/Button";

export interface ErrorBoundaryProps {
  children: ReactNode;
  fallbackTitle?: string;
  fallbackDescription?: string;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("Unhandled UI error captured by ErrorBoundary:", error, errorInfo);
  }

  private handleRetry = (): void => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div role="alert" className="flex flex-col items-center justify-center gap-4 py-24 text-center">
          <h1 className="text-lg font-semibold text-primary">
            {this.props.fallbackTitle ?? "Something went wrong"}
          </h1>
          <p className="max-w-md text-sm text-slate-500">
            {this.props.fallbackDescription ??
              "An unexpected error occurred while rendering this view. You can try again, or navigate elsewhere using the sidebar."}
          </p>
          <Button variant="primary" onClick={this.handleRetry}>
            Try again
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}