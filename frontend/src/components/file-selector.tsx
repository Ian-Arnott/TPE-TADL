"use client";

import { useState } from "react";
import { Check, ChevronsUpDown, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import type { ProjectSelectorProps } from "@/types/report";

export function ProjectSelector({
  selectedProjects,
  onSelectProjects,
  availableProjects,
}: ProjectSelectorProps) {
  const [open, setOpen] = useState(false);

  const handleSelectAuto = () => {
    onSelectProjects(["auto"]);
    setOpen(false);
  };

  const handleSelectProject = (project: string) => {
    // If "auto" is already selected, remove it
    const newSelection = selectedProjects.includes("auto")
      ? [project]
      : selectedProjects.includes(project)
      ? selectedProjects.filter((p: string) => p !== project)
      : [...selectedProjects, project];

    onSelectProjects(newSelection);
  };

  const displayText = selectedProjects.includes("auto")
    ? "Auto-select projects"
    : selectedProjects.length === 0
    ? "Select projects..."
    : `${selectedProjects.length} project${
        selectedProjects.length > 1 ? "s" : ""
      } selected`;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">Projects</label>
        {selectedProjects.length > 0 && !selectedProjects.includes("auto") && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onSelectProjects([])}
            className="h-auto p-0 text-xs text-muted-foreground"
          >
            Clear
          </Button>
        )}
      </div>

      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full justify-between"
          >
            {displayText}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[300px] p-0">
          <Command>
            <CommandInput placeholder="Search projects..." />
            <CommandList>
              <CommandEmpty>No projects found.</CommandEmpty>
            </CommandList>
            <CommandList>
              <CommandGroup>
                <CommandItem
                  onSelect={handleSelectAuto}
                  className="flex items-center"
                >
                  <div className="flex items-center gap-2 flex-1">
                    <span>Auto-select relevant projects</span>
                  </div>
                  {selectedProjects.includes("auto") && (
                    <Check className="h-4 w-4 ml-2" />
                  )}
                </CommandItem>
              </CommandGroup>
            </CommandList>
            <CommandList>
              <CommandGroup heading="Available Projects">
                {availableProjects.map((project: string) => (
                  <CommandItem
                    key={project}
                    onSelect={() => handleSelectProject(project)}
                    className="flex items-center"
                    disabled={selectedProjects.includes("auto")}
                  >
                    <div className="flex items-center gap-2 flex-1">
                      <FileText className="h-4 w-4" />
                      <span>{project}</span>
                    </div>
                    {selectedProjects.includes(project) &&
                      !selectedProjects.includes("auto") && (
                        <Check className="h-4 w-4 ml-2" />
                      )}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {selectedProjects.length > 0 && !selectedProjects.includes("auto") && (
        <div className="flex flex-wrap gap-2 mt-2">
          {selectedProjects.map((project: string) => (
            <Badge
              key={project}
              variant="secondary"
              className="flex items-center gap-1"
            >
              <FileText className="h-3 w-3" />
              {project}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
