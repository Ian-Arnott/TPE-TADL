import os
from typing import List, Optional
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

from tqdm import tqdm

from helpers import export_to_pdf
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.metrics import (
    LLMContextPrecisionWithoutReference,
    context_recall,
    answer_relevancy,
    faithfulness,
)


load_dotenv()

# ─── Configuration ─────────────────────────────────────────────────────────────

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "briefing-index-final"
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "reports.db")

# ─── Embedding dimension ──────────────────────────────────────────────────────
test_embedding = openai.embeddings.create(input="test", model="text-embedding-3-small")
embedding_size = len(test_embedding.data[0].embedding)
print(f"Embedding size: {embedding_size}")

# ─── Pinecone init ────────────────────────────────────────────────────────────

pc = Pinecone(api_key=PINECONE_API_KEY)
print(pc.list_indexes().names())

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

# Add a lock for thread-safe database operations
db_lock = threading.RLock()

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()
cur.execute(
    """
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    title TEXT,
    prompt TEXT,
    projects TEXT,
    createdAt TEXT,
    status TEXT,
    error TEXT,
    download_path TEXT,
    context_precision TEXT,
    context_recall TEXT,
    answer_relevancy TEXT,
    faithfulness TEXT
)
"""
)
cur.execute(
    """
CREATE TABLE IF NOT EXISTS indexed_files (
    file_path TEXT PRIMARY KEY,
    project TEXT,
    last_modified INTEGER,
    last_indexed INTEGER
)
"""
)
conn.commit()


# ─── Embedding & indexing ─────────────────────────────────────────────────────


def embed_text(text: str) -> list[float]:
    resp = openai.embeddings.create(input=text, model="text-embedding-3-small")
    return resp.data[0].embedding


def index_file(filepath: str, project: str, force: bool = False):
    """Parse PDF/DOCX/TXT, split & index into Pinecone."""
    try:
        # Get file's last modification time
        file_mtime = os.path.getmtime(filepath)

        # Check if file has been indexed and hasn't changed
        if not force:
            with db_lock:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT last_modified FROM indexed_files WHERE file_path = ?",
                    (filepath,),
                )
                result = cursor.fetchone()
                cursor.close()
            if result and result[0] == int(file_mtime):
                return  # Skip indexing if file hasn't changed

        if filepath.lower().endswith(".pdf"):
            reader = PdfReader(filepath)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif filepath.lower().endswith(".docx"):
            doc = Document(filepath)
            text = "\n".join(p.text for p in doc.paragraphs)
        elif filepath.lower().endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        elif filepath.lower().endswith(".csv"):
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        elif filepath.lower().endswith(".json"):
            with open(filepath, "r", encoding="utf-8") as f:
                text = str(json.load(f))
        else:
            return

        chunk_size = 500
        overlap = 50
        chunks: List[str] = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i : i + chunk_size])

        # First delete any existing vectors for this file
        try:
            index = get_index()
            index.delete(
                filter={"source": os.path.basename(filepath)}, namespace="main"
            )
        except Exception as e:
            # Do nothing
            pass

        vectors: List[Vector] = []
        for i, chunk in enumerate(chunks):
            emb = embed_text(chunk)
            id = f"{os.path.basename(filepath)}-{i}"
            meta = {
                "source": os.path.basename(filepath),
                "text": chunk,
                "project": project,
            }
            to_append = {"id": id, "values": emb, "metadata": meta}
            vectors.append(to_append)

        index.upsert(vectors=vectors, namespace="main")

        file_mtime = int(file_mtime)
        with db_lock:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO indexed_files (file_path, project, last_modified, last_indexed) VALUES (?, ?, ?, ?)",
                (filepath, project, file_mtime, file_mtime),
            )
            conn.commit()
            cursor.close()
    except Exception as e:
        print(f"Error indexing file {filepath}: {e}")


def index_all_files(force: bool = False):
    files_to_index = []
    for root, dirs, files in os.walk(os.path.join(BASE_DIR, "uploads")):
        for file in files:
            files_to_index.append((root, file))
    for root, file in tqdm(files_to_index, desc="Indexing files"):
        index_file(os.path.join(root, file), os.path.basename(root), force)


index_all_files()
print("Indexing complete")

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


def list_projects():
    """Return all subdirectories in the uploads directory."""
    projects_dir = os.path.join(BASE_DIR, "uploads")
    return [
        name
        for name in os.listdir(projects_dir)
        if os.path.isdir(os.path.join(projects_dir, name))
    ]


# ─── RAGAS evaluation ────────────────────────────────────────────────────────


def run_ragas_eval(
    report_id: str,
    user_instructions: str,
    contexts: list[str],
    result: str,
):
    try:
        ragas_sample = SingleTurnSample(
            user_input=user_instructions,
            retrieved_contexts=contexts,
            response=result,
        )
        dataset = EvaluationDataset([ragas_sample])
        ragas_result = evaluate(
            dataset,
            metrics=[
                LLMContextPrecisionWithoutReference(),
                # context_recall, # No trabajamos con reference
                answer_relevancy,
                faithfulness,
            ],
        )
        print(ragas_result.scores)
        print(ragas_result.scores[0]["llm_context_precision_without_reference"])

        with db_lock:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE reports
                SET context_precision=?, context_recall=?, answer_relevancy=?, faithfulness=?
                WHERE id=?
                """,
                (
                    str(
                        ragas_result.scores[0][
                            "llm_context_precision_without_reference"
                        ]
                    ),
                    "",
                    str(ragas_result.scores[0]["answer_relevancy"]),
                    str(ragas_result.scores[0]["faithfulness"]),
                    report_id,
                ),
            )
            conn.commit()
            cursor.close()
    except Exception as e:
        print(f"Error running RAGAS evaluation: {e}")


# ─── Briefing generation ──────────────────────────────────────────────────────


def generate_briefing(report_id: str, projects: list[str]):
    with db_lock:
        cursor = conn.cursor()
        cursor.execute("SELECT prompt, projects FROM reports WHERE id=?", (report_id,))
        row = cursor.fetchone()
        cursor.close()

    if not row:
        return
    prompt, projects_json = row
    projects = json.loads(projects_json)

    try:
        query_emb = embed_text(prompt)

        index = get_index()
        if "any" in projects:
            query_resp = index.query(
                include_values=True,
                include_metadata=True,
                vector=query_emb,
                top_k=15,
                namespace="main",
            )
        else:
            query_resp = index.query(
                include_values=True,
                include_metadata=True,
                vector=query_emb,
                top_k=15,
                filter={"project": {"$in": projects}},
                namespace="main",
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

        threading.Thread(
            target=run_ragas_eval,
            args=(report_id, user_instructions, contexts, result),
            daemon=True,
        ).start()

        out_dir = os.path.join(BASE_DIR, "reports")
        os.makedirs(out_dir, exist_ok=True)

        txt_outfile = os.path.join(out_dir, f"{report_id}.txt")
        with open(txt_outfile, "w", encoding="utf-8") as f:
            f.write(result)

        pdf_outfile = os.path.join(out_dir, f"{report_id}.pdf")
        export_to_pdf(result, pdf_outfile)

        title = result.split("Briefing: ")[1].split("\n")[0]

        with db_lock:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE reports
                SET status='complete', download_path=?, title=?
                WHERE id=?
            """,
                (pdf_outfile, title, report_id),
            )
            conn.commit()
            cursor.close()

    except Exception as e:
        with db_lock:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE reports
                SET status='failed', error=?
                WHERE id=?
            """,
                (str(e), report_id),
            )
            conn.commit()
            cursor.close()
        print(f"Error generating report {report_id}: {e}")


# ─── Report-management API ────────────────────────────────────────────────────


def create_report(title: str, prompt: str, projects: list[str]) -> dict:
    try:
        report_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        with db_lock:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO reports
                (id, title, prompt, projects, createdAt, status)
                VALUES (?, ?, ?, ?, ?, 'generating')
            """,
                (report_id, title, prompt, json.dumps(projects), now),
            )
            conn.commit()
            cursor.close()

        thread = threading.Thread(target=generate_briefing, args=(report_id, projects))
        thread.daemon = True
        thread.start()

        return {
            "id": report_id,
            "title": title,
            "prompt": prompt,
            "projects": projects,
            "createdAt": now,
            "status": "generating",
        }
    except Exception as e:
        print(f"Error creating report: {e}")
        return {"error": str(e)}


def list_reports() -> list[dict]:
    with db_lock:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports")
        rows = cursor.fetchall()
        cursor.close()

    result = []
    for r in rows:
        result.append(
            {
                "id": r[0],
                "title": r[1],
                "prompt": r[2],
                "projects": json.loads(r[3]),
                "createdAt": r[4],
                "status": r[5],
                "downloadUrl": r[6] if r[6] else None,
                "error": r[7] if r[7] else None,
                "contextPrecision": r[8] if r[8] else None,
                "contextRecall": r[9] if r[9] else None,
                "answerRelevancy": r[10] if r[10] else None,
                "faithfulness": r[11] if r[11] else None,
            }
        )
    return result


def get_report_path(report_id: str) -> Optional[str]:
    with db_lock:
        cursor = conn.cursor()
        cursor.execute("SELECT download_path FROM reports WHERE id=?", (report_id,))
        row = cursor.fetchone()
        cursor.close()
    return row[0] if row else None
