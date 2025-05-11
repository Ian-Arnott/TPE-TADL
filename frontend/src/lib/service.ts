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
  ): Promise<void> {
    try {
      await this.axiosInstance.post("/reports", {
        prompt,
        title,
        files,
      });
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
    return new Blob();
  }
}
