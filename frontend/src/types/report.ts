export interface Report {
  id: string
  title: string
  createdAt: string
  status: ReportStatus
  prompt: string
  files: string[]
  downloadUrl?: string
  error?: string
}

export type ReportStatus = "generating" | "complete" | "failed"

export interface ReportListProps {
  reports: Report[]
  onSelectReport: (reportId: string) => void
  selectedReportId?: string
}

export interface ReportDetailProps {
  report: Report
  onDownload: (reportId: string) => void
}

export interface ReportRequestFormProps {
  onSubmit: (prompt: string, files: string[]) => void
  isSubmitting: boolean
}

export interface FileSelectorProps {
  selectedFiles: string[]
  onSelectFiles: (files: string[]) => void
  availableFiles: string[]
}
