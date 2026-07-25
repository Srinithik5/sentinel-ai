import { SearchX } from "lucide-react";
import { Link } from "react-router-dom";

import { buttonVariants } from "@/components/ui/Button";
import { ROUTES } from "@/routes/paths";

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
      <SearchX className="h-10 w-10 text-slate-300" aria-hidden="true" />
      <div className="space-y-1">
        <h1 className="text-lg font-semibold text-primary">Page not found</h1>
        <p className="text-sm text-slate-500">
          The page you are looking for does not exist or has been moved.
        </p>
      </div>
      <Link to={ROUTES.dashboard} className={buttonVariants({ variant: "primary" })}>
        Back to Dashboard
      </Link>
    </div>
  );
}