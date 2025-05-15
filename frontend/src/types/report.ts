export interface Report {
  id: string;
  title: string;
  createdAt: string;
  status: ReportStatus;
  prompt: string;
  projects: string[];
  downloadUrl?: string;
  error?: string;
  contextPrecision?: string;
  contextRecall?: string;
  answerRelevancy?: string;
  faithfulness?: string;
}

export type ReportStatus = "generating" | "complete" | "failed";

export interface ReportListProps {
  reports: Report[];
  onSelectReport: (reportId: string) => void;
  selectedReportId?: string;
}

export interface ReportDetailProps {
  report: Report;
  onDownload: (reportId: string) => void;
}

export interface ReportRequestFormProps {
  onSubmit: (prompt: string, projects: string[]) => void;
  isSubmitting: boolean;
}

export interface FileSelectorProps {
  selectedFiles: string[];
  onSelectFiles: (files: string[]) => void;
  availableFiles: string[];
  availableProjects: string[];
}

export interface ProjectSelectorProps {
  selectedProjects: string[];
  onSelectProjects: (projects: string[]) => void;
  availableProjects: string[];
}
