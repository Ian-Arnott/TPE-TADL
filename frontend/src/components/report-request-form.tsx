"use client"

import type React from "react"

import { useState } from "react"
import { Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { FileSelector } from "./file-selector"
import type { ReportRequestFormProps } from "@/types/report"

export function ReportRequestForm({ onSubmit, isSubmitting }: ReportRequestFormProps) {
  const [prompt, setPrompt] = useState("")
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])

  // This would typically come from an API
  const availableFiles = [
    "financial_report_2023.pdf",
    "quarterly_results_q1.xlsx",
    "market_analysis.docx",
    "competitor_research.pdf",
    "customer_feedback.csv",
  ]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (prompt.trim() && (selectedFiles.length > 0 || selectedFiles.includes("auto"))) {
      onSubmit(prompt, selectedFiles)
      setPrompt("")
      setSelectedFiles([])
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <FileSelector selectedFiles={selectedFiles} onSelectFiles={setSelectedFiles} availableFiles={availableFiles} />

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
          disabled={isSubmitting || !prompt.trim() || selectedFiles.length === 0}
          className="h-10 w-10 shrink-0"
        >
          <Send className="h-4 w-4" />
          <span className="sr-only">Send</span>
        </Button>
      </div>
    </form>
  )
}
