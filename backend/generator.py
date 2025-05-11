import os
import json
import csv
import asyncio
from openai import AsyncOpenAI
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from docx import Document
from datetime import datetime
from dotenv import load_dotenv

# Initialize AsyncOpenAI client
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=api_key)

# Configuration
projects = ["TADL_RAG_SECRET_PROJECT", "UX_OPENAI_REFACTOR", "ITBA_NEW_AUTHENTICATION_SERVER"]
num_files_per_project = 5
output_dir = "backend/generated_files"  # Relative path for output files

async def generate_ai_content(prompt: str, model: str = "gpt-4.1") -> str:
    """Call OpenAI ChatCompletion to generate content asynchronously."""
    system_message = {
        "role": "system",
        "content": "You are a synthetic data generator. No one reads your output, so you are non verbose. You only return the content requested. No extra formatting, no markdown, nothing. Just the content."
    }
    response = await client.responses.create(
        model=model,
        input=[system_message, {"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.output_text.strip()

async def create_pdf(project: str, i: int, timestamp: str, content: str) -> str:
    """Create a PDF file with the given content."""
    # Ensure directory exists
    project_dir = os.path.join(output_dir, project)
    os.makedirs(project_dir, exist_ok=True)
    
    pdf_filename = f"{project}_summary_{i}_{timestamp}.pdf"
    full_path = os.path.join(project_dir, pdf_filename)
    
    c = canvas.Canvas(full_path, pagesize=letter)
    text_obj = c.beginText(40, 720)
    for line in content.split("\n"):
        text_obj.textLine(line)
    c.drawText(text_obj)
    c.save()
    return pdf_filename

async def create_docx(project: str, i: int, timestamp: str, content: str) -> str:
    """Create a DOCX file with the given content."""
    # Ensure directory exists
    project_dir = os.path.join(output_dir, project)
    os.makedirs(project_dir, exist_ok=True)
    
    docx_filename = f"{project}_brief_{i}_{timestamp}.docx"
    full_path = os.path.join(project_dir, docx_filename)
    
    # Run in thread pool as Document operations are blocking
    def _create_docx():
        doc = Document()
        doc.add_heading(f"{project} Brief #{i}", level=1)
        for para in content.split("\n\n"):
            doc.add_paragraph(para)
        doc.save(full_path)
    
    await asyncio.to_thread(_create_docx)
    return docx_filename

async def create_json(project: str, i: int, timestamp: str, content: str) -> str:
    """Create a JSON file with Slack-style conversation."""
    # Ensure directory exists
    project_dir = os.path.join(output_dir, project)
    os.makedirs(project_dir, exist_ok=True)
    
    json_filename = f"{project}_chat_{i}_{timestamp}.json"
    full_path = os.path.join(project_dir, json_filename)
    
    messages = json.loads(content)
    
    # File operations can block, so use asyncio.to_thread
    await asyncio.to_thread(
        lambda: json.dump(messages, open(full_path, "w", encoding="utf-8"), indent=2)
    )
    return json_filename

async def create_csv(project: str, i: int, timestamp: str, content: str) -> str:
    """Create a CSV file with the given content."""
    # Ensure directory exists
    project_dir = os.path.join(output_dir, project)
    os.makedirs(project_dir, exist_ok=True)
    
    csv_filename = f"{project}_metrics_{i}_{timestamp}.csv"
    full_path = os.path.join(project_dir, csv_filename)
    
    # File operations can block, so use asyncio.to_thread
    await asyncio.to_thread(
        lambda: open(full_path, "w", newline="", encoding="utf-8").write(content)
    )
    return csv_filename

async def process_file_set(project: str, i: int):
    """Process a complete set of files for a project."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Generate all content concurrently
    pdf_content_task = generate_ai_content(
        f"Write a brief project update summary for '{project}', about 150 words."
    )
    docx_content_task = generate_ai_content(
        f"Create a Project Brief with headings and bullet points for '{project}'."
    )
    json_content_task = generate_ai_content(
        f"Generate a JSON array of 5 Slack-style messages between two team members discussing '{project}' progress. "
        "Each message should include `user`, `text`, and `ts` fields."
    )
    csv_content_task = generate_ai_content(
        f"Provide CSV-formatted project metrics for '{project}' with columns: date, metric, value. Include 5 rows."
    )
    
    # Await all content generation tasks
    pdf_content, docx_content, json_content, csv_content = await asyncio.gather(
        pdf_content_task, docx_content_task, json_content_task, csv_content_task
    )
    
    # Create all files concurrently
    pdf_task = create_pdf(project, i, timestamp, pdf_content)
    docx_task = create_docx(project, i, timestamp, docx_content)
    json_task = create_json(project, i, timestamp, json_content)
    csv_task = create_csv(project, i, timestamp, csv_content)
    
    # Await all file creation tasks
    pdf_filename, docx_filename, json_filename, csv_filename = await asyncio.gather(
        pdf_task, docx_task, json_task, csv_task
    )
    
    project_dir = os.path.join(output_dir, project)
    print(f"Generated files for {project} in {project_dir}: {pdf_filename}, {docx_filename}, {json_filename}, {csv_filename}")

async def main():
    """Main entry point for the script."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving all generated files to directory: {os.path.abspath(output_dir)}")
    
    # Create tasks for all file sets across all projects
    tasks = []
    for project in projects:
        for i in range(1, num_files_per_project + 1):
            tasks.append(process_file_set(project, i))
    
    # Run all tasks concurrently
    await asyncio.gather(*tasks)
    print(f"Completed generating {len(tasks)} file sets in {output_dir}")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())