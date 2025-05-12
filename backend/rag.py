import os
from typing import List
import uuid
import json
import threading
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec, Vector
from pypdf import PdfReader
from docx import Document

from helpers import export_to_pdf

load_dotenv()

# ─── Configuration ─────────────────────────────────────────────────────────────

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "briefing-index-3"

# ─── Embedding dimension ──────────────────────────────────────────────────────
test_embedding = openai.embeddings.create(input="test", model="text-embedding-3-small")
embedding_size = len(test_embedding.data[0].embedding)
print(f"Embedding size: {embedding_size}")

# ─── Pinecone init ────────────────────────────────────────────────────────────

pc = Pinecone(api_key=PINECONE_API_KEY)

if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=embedding_size,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )


def get_index():
    return pc.Index(INDEX_NAME)


# ─── SQLite (for report tracking) ───────────────────────────────────────────────

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "reports.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()
cur.execute(
    """
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    title TEXT,
    prompt TEXT,
    files TEXT,
    createdAt TEXT,
    status TEXT,
    error TEXT,
    download_path TEXT
)
"""
)
conn.commit()

# ─── File utilities ────────────────────────────────────────────────────────────


def list_available_files():
    """Recursively walk through the uploads directory and return all files."""
    upload_dir = os.path.join(BASE_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    files = []
    for root, _, filenames in os.walk(upload_dir):
        rel_path = os.path.relpath(root, upload_dir)
        for filename in filenames:
            if rel_path == ".":
                files.append(filename)
            else:
                files.append(os.path.join(rel_path, filename))

    return files


# ─── Embedding & indexing ─────────────────────────────────────────────────────


def embed_text(text: str) -> list[float]:
    resp = openai.embeddings.create(input=text, model="text-embedding-3-small")
    return resp.data[0].embedding


def index_file(filepath: str):
    """Parse PDF/DOCX/TXT, split & index into Pinecone."""
    try:
        if filepath.lower().endswith(".pdf"):
            reader = PdfReader(filepath)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif filepath.lower().endswith(".docx"):
            doc = Document(filepath)
            text = "\n".join(p.text for p in doc.paragraphs)
        elif filepath.lower().endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            return

        chunk_size = 500
        overlap = 50
        chunks: List[str] = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i : i + chunk_size])

        index = get_index()
        vectors: List[Vector] = []
        for i, chunk in enumerate(chunks):
            emb = embed_text(chunk)
            id = f"{os.path.basename(filepath)}-{i}"
            meta = {"source": os.path.basename(filepath), "text": chunk}
            to_append = {"id": id, "values": emb, "metadata": meta}
            vectors.append(to_append)

        index.upsert(vectors=vectors)
    except Exception as e:
        print(f"Error indexing file {filepath}: {e}")


# ─── Briefing generation ──────────────────────────────────────────────────────


def generate_briefing(report_id: str):
    cur = conn.cursor()
    cur.execute("SELECT prompt, files FROM reports WHERE id=?", (report_id,))
    row = cur.fetchone()
    if not row:
        return
    prompt, files_json = row
    files = json.loads(files_json)

    try:
        query_emb = embed_text(prompt)

        index = get_index()
        query_resp = index.query(
            include_values=True,
            include_metadata=True,
            vector=query_emb,
            top_k=10,
            filter={"source": {"$in": files}},
        )
        contexts = [match["metadata"]["text"] for match in query_resp["matches"]]
        context = "\n\n".join(contexts) if contexts else ""

        system_msg = {
            "role": "system",
            "content": "Sos un asistente que genera briefings para distintos equipos de trabajo. El briefing debe ser en español, con formato markdown. Es muy importante unicamente incluir la información relevante y real para el equipo en cuestión.",
        }
        user_instructions = f"""
            Genera un briefing con secciones usando markdown:
            # Briefing: <Titulo del reporte>
            
            ## Actividades recientes
            * Usa viñetas para listar actividades
            * Destaca información importante en **negrita**
            
            ## Problemas o bloqueos
            * Usa viñetas para listar problemas
            * Usa *cursiva* para información contextual
            
            ## Interacciones con otros equipos
            
            ## KPIs
            
            ## Tareas planificadas
            * Usa viñetas para listar tareas

            ---
            Si no hay información para una sección, escribe "No hay información disponible".
            ---

            Prompt: {prompt}

            Contexto relevante extraído:
            {context}
        """.strip()

        chat_resp = openai.responses.create(
            model="gpt-4.1",
            input=[system_msg, {"role": "user", "content": user_instructions}],
            temperature=0.3,
        )
        result = chat_resp.output_text.strip()

        out_dir = os.path.join(BASE_DIR, "reports")
        os.makedirs(out_dir, exist_ok=True)

        txt_outfile = os.path.join(out_dir, f"{report_id}.txt")
        with open(txt_outfile, "w", encoding="utf-8") as f:
            f.write(result)

        pdf_outfile = os.path.join(out_dir, f"{report_id}.pdf")
        export_to_pdf(result, pdf_outfile)

        title = result.split("Briefing: ")[1].split("\n")[0]

        cur.execute(
            """
            UPDATE reports
            SET status='complete', download_path=?, title=?
            WHERE id=?
        """,
            (pdf_outfile, title, report_id),
        )
        conn.commit()

    except Exception as e:
        cur.execute(
            """
            UPDATE reports
            SET status='failed', error=?
            WHERE id=?
        """,
            (str(e), report_id),
        )
        conn.commit()
        print(f"Error generating report {report_id}: {e}")


# ─── Report-management API ────────────────────────────────────────────────────


def create_report(title: str, prompt: str, files: list[str]) -> dict:
    try:

        upload_dir = os.path.join(BASE_DIR, "uploads")
        for filename in files:
            path = os.path.join(upload_dir, filename)
            if os.path.exists(path):
                index_file(path)

        report_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO reports
            (id, title, prompt, files, createdAt, status)
            VALUES (?, ?, ?, ?, ?, 'generating')
        """,
            (report_id, title, prompt, json.dumps(files), now),
        )
        conn.commit()

        thread = threading.Thread(target=generate_briefing, args=(report_id,))
        thread.daemon = True
        thread.start()

        return {
            "id": report_id,
            "title": title,
            "prompt": prompt,
            "files": files,
            "createdAt": now,
            "status": "generating",
        }
    except Exception as e:
        print(f"Error creating report: {e}")
        return {"error": str(e)}


def list_reports() -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, prompt, files, createdAt, status, download_path, error FROM reports"
    )
    rows = cur.fetchall()
    result = []
    for r in rows:
        result.append(
            {
                "id": r[0],
                "title": r[1],
                "prompt": r[2],
                "files": json.loads(r[3]),
                "createdAt": r[4],
                "status": r[5],
                "downloadUrl": r[6] if r[6] else None,
                "error": r[7] if r[7] else None,
            }
        )
    return result


def get_report_path(report_id: str) -> str | None:
    cur = conn.cursor()
    cur.execute("SELECT download_path FROM reports WHERE id=?", (report_id,))
    row = cur.fetchone()
    return row[0] if row else None
