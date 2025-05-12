"use client";

import type React from "react";

import { useEffect, useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ProjectSelector } from "./file-selector";
import type { ReportRequestFormProps } from "@/types/report";
import { set } from "date-fns";
import { ApiService } from "@/lib/service";

export function ReportRequestForm({
  onSubmit,
  isSubmitting,
}: ReportRequestFormProps) {
  const [prompt, setPrompt] = useState("");
  const [selectedProjects, setSelectedProjects] = useState<string[]>([]);
  const [availableProjects, setAvailableProjects] = useState<string[]>([]);
  const apiService = new ApiService();

  useEffect(() => {
    const fetchProjects = async () => {
      setAvailableProjects(await apiService.getAvailableProjects());
    };
    fetchProjects();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (
      prompt.trim() &&
      (selectedProjects.length > 0 || selectedProjects.includes("auto"))
    ) {
      onSubmit(prompt, selectedProjects);
      setPrompt("");
      setSelectedProjects([]);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <ProjectSelector
        selectedProjects={selectedProjects}
        onSelectProjects={setSelectedProjects}
        availableProjects={availableProjects}
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
            isSubmitting || !prompt.trim() || selectedProjects.length === 0
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
