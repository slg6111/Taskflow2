from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import date
import heapq
import json
import os

app = Flask(__name__)
CORS(app, origins=["https://taskflow-2579.netlify.app"])

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"tasks": [], "last_reset": str(date.today()), "projects": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def maybe_reset_tasks(data):
    today = str(date.today())
    if data.get("last_reset") != today:
        for task in data["tasks"]:
            task["completed"] = False
        data["last_reset"] = today
        save_data(data)
    return data

# ── Daily Tasks ──────────────────────────────────────────────────────────────

@app.route("/tasks", methods=["GET"])
def get_tasks():
    data = maybe_reset_tasks(load_data())
    return jsonify(data["tasks"])

@app.route("/tasks", methods=["POST"])
def add_task():
    data = maybe_reset_tasks(load_data())
    body = request.json
    task = {
        "id": int(date.today().strftime("%Y%m%d%H%M%S") + str(len(data["tasks"]))),
        "name": body["name"],
        "completed": False
    }
    data["tasks"].append(task)
    save_data(data)
    return jsonify(task), 201

@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    data = load_data()
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    save_data(data)
    return jsonify({"ok": True})

@app.route("/tasks/<int:task_id>/complete", methods=["PATCH"])
def toggle_task(task_id):
    data = maybe_reset_tasks(load_data())
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["completed"] = not task["completed"]
            save_data(data)
            return jsonify(task)
    return jsonify({"error": "Not found"}), 404

# ── Projects ─────────────────────────────────────────────────────────────────

def heapsort_projects(projects):
    """Sort projects by due_date using heapq (min-heap)."""
    heap = [(p["due_date"], i, p) for i, p in enumerate(projects)]
    heapq.heapify(heap)
    return [heapq.heappop(heap)[2] for _ in range(len(heap))]

def build_graph(sorted_projects):
    """Build adjacency list: each project points to the next (linked chain)."""
    graph = {}
    for i, proj in enumerate(sorted_projects):
        pid = proj["id"]
        graph[pid] = {
            "project": proj,
            "edges": [sorted_projects[i + 1]["id"]] if i + 1 < len(sorted_projects) else []
        }
    return graph

@app.route("/projects", methods=["GET"])
def get_projects():
    data = load_data()
    sorted_projects = heapsort_projects(data["projects"])
    graph = build_graph(sorted_projects)
    return jsonify({"sorted": sorted_projects, "graph": graph})

@app.route("/projects", methods=["POST"])
def add_project():
    data = load_data()
    body = request.json
    project = {
        "id": int(date.today().strftime("%Y%m%d%H%M%S") + str(len(data["projects"]))),
        "name": body["name"],
        "due_date": body["due_date"],
        "completed": False
    }
    data["projects"].append(project)
    save_data(data)
    return jsonify(project), 201

@app.route("/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    data = load_data()
    data["projects"] = [p for p in data["projects"] if p["id"] != project_id]
    save_data(data)
    return jsonify({"ok": True})

@app.route("/projects/<int:project_id>/complete", methods=["PATCH"])
def toggle_project(project_id):
    data = load_data()
    for proj in data["projects"]:
        if proj["id"] == project_id:
            proj["completed"] = not proj["completed"]
            save_data(data)
            return jsonify(proj)
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
