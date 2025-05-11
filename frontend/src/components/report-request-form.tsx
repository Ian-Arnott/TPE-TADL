"use client";

import type React from "react";

import { useEffect, useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { FileSelector } from "./file-selector";
import type { ReportRequestFormProps } from "@/types/report";
import { set } from "date-fns";
import { ApiService } from "@/lib/service";

export function ReportRequestForm({
  onSubmit,
  isSubmitting,
}: ReportRequestFormProps) {
  const [prompt, setPrompt] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [availableFiles, setAvailableFiles] = useState<string[]>([]);
  const apiService = new ApiService();

  useEffect(() => {
    const fetchFiles = async () => {
      setAvailableFiles(await apiService.getAvailableFiles());
    };
    fetchFiles();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (
      prompt.trim() &&
      (selectedFiles.length > 0 || selectedFiles.includes("auto"))
    ) {
      onSubmit(prompt, selectedFiles);
      setPrompt("");
      setSelectedFiles([]);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <FileSelector
        selectedFiles={selectedFiles}
        onSelectFiles={setSelectedFiles}
        availableFiles={availableFiles}
      />

      <div className="flex items-end gap-2">
        <Textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the report you want to generate..."
          className="min-h-[100px] flex-1"
          disabled={isSubmitting}
        />
        <Button
          type="submit"
          size="icon"
          disabled={
            isSubmitting || !prompt.trim() || selectedFiles.length === 0
          }
          className="h-10 w-10 shrink-0"
        >
          <Send className="h-4 w-4" />
          <span className="sr-only">Send</span>
        </Button>
      </div>
    </form>
  );
}
