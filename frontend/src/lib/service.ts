import axios, { AxiosInstance } from "axios";
import { Report } from "@/types/report";

export class ApiService {
  axiosInstance: AxiosInstance;

  constructor() {
    this.axiosInstance = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  async getReports(): Promise<Report[]> {
    try {
      const response = await this.axiosInstance.get("/reports");
      return response.data;
    } catch (error) {
      console.error("Error fetching reports:", error);
      throw error;
    }
  }

  async createReport(
    prompt: string,
    title: string,
    files: string[]
  ): Promise<Report> {
    try {
      const response = await this.axiosInstance.post("/reports/generate", {
        prompt,
        title,
        files,
      });
      return response.data as Report;
    } catch (error) {
      console.error("Error creating report:", error);
      throw error;
    }
  }

  async getAvailableFiles(): Promise<string[]> {
    try {
      const response = await this.axiosInstance.get("/files/available");
      return response.data;
    } catch (error) {
      console.error("Error fetching available files:", error);
      throw error;
    }
  }

  async downloadReport(reportId: string): Promise<Blob> {
    try {
      const response = await this.axiosInstance.get(`/reports/download/${reportId}`);
      return new Blob([response.data], { type: "application/pdf" });
    } catch (error) {
      console.error("Error downloading report:", error);
      throw error;
    }
  }

  async uploadFile(files: File[]): Promise<void> {
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);

        await this.axiosInstance.post("/files/upload", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });
      }
    } catch (error) {
      console.error("Error uploading file:", error);
      throw error;
    }
  }
}
