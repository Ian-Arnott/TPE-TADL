"use client";

import { useState, useEffect } from "react";
import { Download, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import type { ReportDetailProps } from "@/types/report";
import { Document, Page, pdfjs } from "react-pdf";
import { ApiService } from "@/lib/service";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

export function ReportDetail({ report, onDownload }: ReportDetailProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const apiService = new ApiService();

  useEffect(() => {
    setNumPages(null);
    setPageNumber(1);
    setPdfBlob(null);

    if (report?.status === "complete" && report.downloadUrl) {
      const loadPdf = async () => {
        try {
          if (pdfBlob && pdfFile) return;

          const response = await apiService.downloadReport(report.id);
          setPdfBlob(response);
          setPdfFile(
            new File([response], "report.pdf", { type: "application/pdf" })
          );
        } catch (error) {
          console.error("Error fetching PDF:", error);
        }
      };
      console.log("Loading PDF for report:", report.id);
      loadPdf();
    }
  }, [report?.id, report?.status, report?.downloadUrl]);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
  }

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
              {pdfBlob ? (
                <div
                  className="pdf-container"
                  style={{ height: "500px", overflow: "auto" }}
                >
                  <Document
                    file={pdfFile}
                    onLoadSuccess={onDocumentLoadSuccess}
                    loading={<p>Loading PDF...</p>}
                    error={<p>Failed to load PDF document.</p>}
                  >
                    {numPages && (
                      <Page
                        pageNumber={pageNumber}
                        scale={1.0}
                        renderTextLayer={true}
                        renderAnnotationLayer={true}
                      />
                    )}
                  </Document>
                  {numPages && (
                    <div className="pdf-controls flex justify-between mt-2">
                      <Button
                        variant="outline"
                        onClick={() =>
                          setPageNumber(Math.max(1, pageNumber - 1))
                        }
                        disabled={pageNumber <= 1}
                      >
                        Previous
                      </Button>
                      <p className="text-center">
                        Page {pageNumber} of {numPages}
                      </p>
                      <Button
                        variant="outline"
                        onClick={() =>
                          setPageNumber(Math.min(numPages, pageNumber + 1))
                        }
                        disabled={pageNumber >= numPages}
                      >
                        Next
                      </Button>
                    </div>
                  )}
                </div>
              ) : (
                <p>Loading preview...</p>
              )}
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
