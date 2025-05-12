"use client";

import { use, useEffect, useState } from "react";
import { ReportList } from "@/components/report-list";
import { ReportDetail } from "@/components/report-detail";
import { ReportRequestForm } from "@/components/report-request-form";
import type { Report } from "@/types/report";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiService } from "@/lib/service";

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const apiService = new ApiService();

  const [selectedReportId, setSelectedReportId] = useState<string | undefined>(
    reports[0]?.id
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState("reports");

  const selectedReport = reports.find(
    (report) => report.id === selectedReportId
  );

  const fetchReports = async () => {
    const data = await apiService.getReports();
    setReports(data);
  };

  useEffect(() => {
    const interval = setInterval(() => {
      fetchReports();
    }, 1000);

    fetchReports();
  }, []);

  const handleSubmitRequest = async (prompt: string, files: string[]) => {
    setIsSubmitting(true);
    setSelectedReportId(undefined);

    try {
      await apiService.createReport(prompt, "New Report", files);
      fetchReports();
    } catch (error) {
      console.error("Error submitting report request:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDownload = async (reportId: string) => {
    const blob = await apiService.downloadReport(reportId);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${reportId}.pdf`;
    document.body.appendChild(a);
    a.click();
    fetchReports();
  };

  return (
    <div className="container mx-auto py-6 max-w-7xl">
      <h1 className="text-3xl font-bold mb-6">Report Generation</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1">
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="w-full"
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="reports">Reports</TabsTrigger>
              <TabsTrigger value="new">New Report</TabsTrigger>
            </TabsList>

            <TabsContent value="reports" className="mt-4">
              <ReportList
                reports={reports}
                onSelectReport={setSelectedReportId}
                selectedReportId={selectedReportId}
              />
            </TabsContent>

            <TabsContent value="new" className="mt-4">
              <ReportRequestForm
                onSubmit={handleSubmitRequest}
                isSubmitting={isSubmitting}
              />
            </TabsContent>
          </Tabs>
        </div>

        <div className="md:col-span-2">
          <ReportDetail
            report={selectedReport as Report}
            onDownload={handleDownload}
          />
        </div>
      </div>
    </div>
  );
}
