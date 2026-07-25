import { ShieldAlert } from "lucide-react";

import { PageHeader } from "@/components/ui/PageHeader";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@/components/ui/Table";

export default function AlertsPage() {
  return (
    <>
      <PageHeader
        title="Alerts"
        description="Security alerts generated from anomalous behavioral signals will be triaged here."
      />
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableHeaderCell>Severity</TableHeaderCell>
              <TableHeaderCell>Entity</TableHeaderCell>
              <TableHeaderCell>Signal</TableHeaderCell>
              <TableHeaderCell>Detected</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              <TableCell colSpan={4}>
                <div className="flex flex-col items-center gap-3 py-12 text-center">
                  <ShieldAlert className="h-8 w-8 text-slate-300" aria-hidden="true" />
                  <p className="text-sm text-slate-500">
                    No alerts to display yet. This view will populate once the detection engine
                    is enabled.
                  </p>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
}