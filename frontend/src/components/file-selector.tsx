"use client"

import { useState } from "react"
import { Check, ChevronsUpDown, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Badge } from "@/components/ui/badge"
import type { FileSelectorProps } from "@/types/report"

export function FileSelector({ selectedFiles, onSelectFiles, availableFiles }: FileSelectorProps) {
  const [open, setOpen] = useState(false)

  const handleSelectAuto = () => {
    onSelectFiles(["auto"])
    setOpen(false)
  }

  const handleSelectFile = (file: string) => {
    // If "auto" is already selected, remove it
    const newSelection = selectedFiles.includes("auto")
      ? [file]
      : selectedFiles.includes(file)
        ? selectedFiles.filter((f) => f !== file)
        : [...selectedFiles, file]

    onSelectFiles(newSelection)
  }

  const displayText = selectedFiles.includes("auto")
    ? "Auto-select files"
    : selectedFiles.length === 0
      ? "Select files..."
      : `${selectedFiles.length} file${selectedFiles.length > 1 ? "s" : ""} selected`

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">Context Files</label>
        {selectedFiles.length > 0 && !selectedFiles.includes("auto") && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onSelectFiles([])}
            className="h-auto p-0 text-xs text-muted-foreground"
          >
            Clear
          </Button>
        )}
      </div>

      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" role="combobox" aria-expanded={open} className="w-full justify-between">
            {displayText}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[300px] p-0">
          <Command>
            <CommandInput placeholder="Search files..." />
            <CommandList>
              <CommandEmpty>No files found.</CommandEmpty>
            </CommandList>
            <CommandList>
              <CommandGroup>
                <CommandItem onSelect={handleSelectAuto} className="flex items-center">
                  <div className="flex items-center gap-2 flex-1">
                    <span>Auto-select relevant files</span>
                  </div>
                  {selectedFiles.includes("auto") && <Check className="h-4 w-4 ml-2" />}
                </CommandItem>
              </CommandGroup>
            </CommandList>
            <CommandList>
              <CommandGroup heading="Available Files">
                {availableFiles.map((file) => (
                  <CommandItem
                    key={file}
                    onSelect={() => handleSelectFile(file)}
                    className="flex items-center"
                    disabled={selectedFiles.includes("auto")}
                  >
                    <div className="flex items-center gap-2 flex-1">
                      <FileText className="h-4 w-4" />
                      <span>{file}</span>
                    </div>
                    {selectedFiles.includes(file) && !selectedFiles.includes("auto") && (
                      <Check className="h-4 w-4 ml-2" />
                    )}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {selectedFiles.length > 0 && !selectedFiles.includes("auto") && (
        <div className="flex flex-wrap gap-2 mt-2">
          {selectedFiles.map((file) => (
            <Badge key={file} variant="secondary" className="flex items-center gap-1">
              <FileText className="h-3 w-3" />
              {file}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}
