import { Boxes } from "lucide-react";

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

export default function EntitiesPage() {
  return (
    <>
      <PageHeader
        title="Entities"
        description="Users, hosts, and devices being monitored for behavioral anomalies."
      />
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableHeaderCell>Entity</TableHeaderCell>
              <TableHeaderCell>Type</TableHeaderCell>
              <TableHeaderCell>Risk Score</TableHeaderCell>
              <TableHeaderCell>Last Seen</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              <TableCell colSpan={4}>
                <div className="flex flex-col items-center gap-3 py-12 text-center">
                  <Boxes className="h-8 w-8 text-slate-300" aria-hidden="true" />
                  <p className="text-sm text-slate-500">
                    No entities to display yet. This view will populate once entity monitoring
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