"use client";

import { Download, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import type { ReportDetailProps } from "@/types/report";

export function ReportDetail({ report, onDownload }: ReportDetailProps) {
  if (!report) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">Select a report to view details</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">{report.title}</h2>
        {report.status === "complete" && report.downloadUrl && (
          <Button onClick={() => onDownload(report.id)} className="gap-2">
            <Download className="h-4 w-4" />
            Download Report
          </Button>
        )}
      </div>

      {report.status === "failed" && report.error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{report.error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Report Request</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-wrap">{report.prompt}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Files Used</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc pl-5 space-y-1">
            {report.files.includes("auto") ? (
              <li>Auto-selected relevant files</li>
            ) : (
              report.files.map((file) => <li key={file}>{file}</li>)
            )}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Report Preview</CardTitle>
        </CardHeader>
        <CardContent>
          {report.status === "generating" ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-full" />
            </div>
          ) : report.status === "complete" ? (
            <div className="prose max-w-none">
              <p>
                This is a preview of the generated report. Download the full
                report to view all content.
              </p>
              {/* This would typically contain a preview of the report content */}
            </div>
          ) : (
            <p className="text-muted-foreground">
              Report generation failed. Please try again.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
