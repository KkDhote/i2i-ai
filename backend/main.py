import os
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from fastapi import HTTPException
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

app = FastAPI(
    title="AdaptIQ AI API",
    description="AI-powered business productivity and task insights",
    version="1.0.0",
)

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# Allow requests from the local React + Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""


tasks = [
    {
        "id": 1,
        "title": "Review quarterly performance",
        "description": "Prepare the quarterly business review",
        "status": "In Progress",
    },
    {
        "id": 2,
        "title": "Analyze team productivity",
        "description": "Identify workload bottlenecks",
        "status": "Pending",
    },
]


@app.get("/")
def root():
    return {"message": "Welcome to AdaptIQ AI API"}


@app.get("/api/health")
def health():
    return {"status": "healthy", "app": "AdaptIQ AI"}


@app.get("/api/overview")
def overview():
    completed = sum(t["status"] == "Completed" for t in tasks)
    return {
        "total_tasks": len(tasks),
        "completed_tasks": completed,
        "pending_tasks": len(tasks) - completed,
    }


@app.get("/api/tasks")
def get_tasks():
    return tasks


@app.post("/api/tasks", status_code=201)
def create_task(task: TaskCreate):
    new_task = {
        "id": max((t["id"] for t in tasks), default=0) + 1,
        "title": task.title,
        "description": task.description or "",
        "status": "Pending",
    }
    tasks.append(new_task)
    return new_task


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, status: str):
    allowed_statuses = {"Pending", "In Progress", "Completed"}

    if status not in allowed_statuses:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid task status")

    for task in tasks:
        if task["id"] == task_id:
            task["status"] = status
            return task

    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Task not found")

class AIQuestion(BaseModel):
    question: str


@app.post("/api/ai/ask")
def ask_ai(request: AIQuestion):
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key is not configured.",
        )

    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please enter a question.",
        )

    task_summary = "\n".join(
        f"- {task['title']} | Status: {task['status']}"
        for task in tasks
    )

    prompt = f"""
You are AdaptIQ AI, a concise business productivity assistant.
Answer the user's business question using the task data below.
Clearly distinguish observations from recommendations.
If the data is insufficient, say so instead of inventing facts.

Current workspace tasks:
{task_summary or "No tasks available."}

User question:
{question}
"""

    
    try:
        models_to_try = [
            "gemini-3.5-flash",
            "gemini-flash-lite-latest",
        ]

        last_error = None

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                if response.text:
                    return {"answer": response.text}

                last_error = f"{model_name} returned an empty response."

            except Exception as e:
                last_error = str(e)
                print(
                    f"Gemini error with {model_name}: {repr(e)}",
                    flush=True,
                )

        raise HTTPException(
            status_code=502,
            detail=f"All configured Gemini models failed: {last_error}",
        )

    except HTTPException:
        raise
    except Exception as e:
        print("Gemini API error:", repr(e), flush=True)
        raise HTTPException(
            status_code=502,
            detail="Gemini request failed. Check the backend terminal.",
        )
