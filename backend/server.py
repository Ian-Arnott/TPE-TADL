import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from rag import (
    list_available_files,
    index_file,
    create_report,
    list_reports,
    get_report_path
)

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/files/available", methods=["GET"])
def available_files():
    files = list_available_files()
    return jsonify(files), 200

@app.route("/files/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "no file part"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "no filename"}), 400

    save_path = os.path.join(UPLOAD_DIR, f.filename)
    f.save(save_path)
    # immediately index into Pinecone
    index_file(save_path)
    return jsonify({"filename": f.filename}), 200

@app.route("/reports/", methods=["GET"])
def get_reports():
    return jsonify(list_reports()), 200

@app.route("/reports/generate", methods=["POST"])
def generate_report_endpoint():
    data = request.json or {}
    title = data.get("title")
    prompt = data.get("prompt")
    files = data.get("selectedFiles", [])
    if not title or not prompt or not isinstance(files, list):
        return jsonify({"error": "invalid payload"}), 400

    report = create_report(title, prompt, files)
    return jsonify(report), 202

@app.route("/reports/download/<report_id>", methods=["GET"])
def download_report(report_id):
    path = get_report_path(report_id)
    if not path or not os.path.exists(path):
        return jsonify({"error": "report not ready or not found"}), 404

    return send_file(path, as_attachment=True, attachment_filename=f"{report_id}.txt")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
