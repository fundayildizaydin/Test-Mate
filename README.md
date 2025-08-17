1. Overview

TestMate is a minimal proof-of-concept (MVP) that generates unit tests for Python code using an LLM API.

Users can paste Python code into the web interface.

The backend sends this code to a Large Language Model (LLM) and retrieves generated tests.

Users can edit, copy, and download the generated tests.

Both frontend (React) and backend (FastAPI) are containerized with Docker.

Accessible at: http://13.48.104.125/

2. Project Structure
/ai-test-generator
 ├── backend/ (FastAPI)
 │    └── main.py
 │    └── Dockerfile 
 ├── frontend/ (React + Vite)
 │    ├── App.tsx
 │    └── index.html
 │    └── Dockerfile 
 │    └── nginx.conf 
 ├── docker-compose.yml
 ├── docs/
 │    ├── Documentation.pdf
 │    └── C4_overview.png
 │    └── samples.py
 

3. Requirements

Docker & Docker Compose

Internet access (to reach Hugging Face LLM API)

4. Installation & Run
# Clone repository
git clone <your-repo-url>
cd ai-test-generator

# Build and start containers
docker compose up --build


Now open: http://localhost:80 (local)
Or deployed version (deployed on AWS EC2): http://13.48.104.125/

5. How to Use

Paste your Python function into the Source Code editor.

Click Generate Tests.

The backend requests the Hugging Face API:

CHAT_URL = "https://router.huggingface.co/v1/chat/completions"

MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct:novita"

The generated pytest code will appear on the right.

You can edit, copy, or download it.

Example in samples.py.

6. Documentation

See /docs/Documentation.pdf for project description.

See /docs/C4_overview.png for system architecture (C4 model).
