"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { formatDistanceToNow } from "date-fns";
import type { ReportListProps } from "@/types/report";

export function ReportList({
  reports,
  onSelectReport,
  selectedReportId,
}: ReportListProps) {
  return (
    <ScrollArea className="h-[calc(100vh-180px)]">
      <div className="space-y-4 p-4">
        {reports.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-center text-muted-foreground">
              No reports generated yet
            </CardContent>
          </Card>
        ) : (
          reports.map((report) => (
            <Card
              key={report.id}
              className={`cursor-pointer transition-all hover:shadow-md ${
                selectedReportId === report.id ? "border-primary" : ""
              }`}
              onClick={() => onSelectReport(report.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <h3 className="font-medium line-clamp-1">{report.title}</h3>
                    <p className="text-sm text-muted-foreground">
                      {formatDistanceToNow(new Date(report.createdAt), {
                        addSuffix: true,
                      })}
                    </p>
                  </div>
                  <StatusBadge status={report.status} />
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </ScrollArea>
  );
}

function StatusBadge({
  status,
}: {
  status: "generating" | "complete" | "failed";
}) {
  const variants = {
    generating: "bg-yellow-100 text-yellow-800 border-yellow-200",
    complete: "bg-green-100 text-green-800 border-green-200",
    failed: "bg-red-100 text-red-800 border-red-200",
  };

  return (
    <Badge variant="outline" className={`${variants[status]}`}>
      {status}
    </Badge>
  );
}
