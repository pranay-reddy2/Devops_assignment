# Session 21 – TaskBoard: Running a Full-Stack App with Docker Compose

TaskBoard is a project-management app made of three parts:

| Service | Tech | Port |
|---|---|---|
| `frontend` | React + Vite, served by nginx | `3000 -> 80` |
| `backend` | FastAPI + SQLAlchemy + Alembic | `8000` |
| `postgres` | PostgreSQL 16 | `5432` |

```
Browser ──> frontend (nginx :80) ──/api──> backend (FastAPI :8000) ──> postgres (:5432)
```

The instructor's full session notes (CI/CD, Terraform, EKS, Helm, monitoring) are in [instructor-notes.md](instructor-notes.md).

## Project files

```
session21-python/
├── backend/
│   ├── Dockerfile          # python:3.12-slim, non-root user, runs alembic then uvicorn
│   ├── app/                # FastAPI app (main.py, models, schemas, db, config)
│   ├── alembic/            # database migrations
│   └── tests/test_api.py   # pytest
├── frontend/
│   ├── Dockerfile          # multi-stage: node:22-alpine build -> nginx:1.27-alpine
│   ├── nginx.conf          # serves the React build, proxies /api to the backend
│   └── src/
└── docker-compose.yml      # postgres + backend + frontend
```

---

## Part 1 – Run the application manually

### 1. PostgreSQL and backend

```bash
# PostgreSQL
docker run -d --name taskboard-postgres \
  -e POSTGRES_DB=taskboard -e POSTGRES_USER=taskboard -e POSTGRES_PASSWORD=taskboard \
  -p 5432:5432 postgres:16-alpine

# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://taskboard:taskboard@localhost:5432/taskboard'
alembic upgrade head
uvicorn app.main:app --port 8000
```

![manual postgres + backend](screenshots/01-manual-postgres-backend.png)

### 2. Unit tests (pytest)

```bash
cd backend && pytest -v
```

![pytest](screenshots/02-pytest.png)

### 3. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, /api is proxied to the backend on :8000
```

![manual frontend](screenshots/03-manual-frontend.png)

The app at http://localhost:5173 reads its tasks from the backend and PostgreSQL:

![manual app in browser](screenshots/04-manual-app-browser.png)

---

## Part 2 – Run everything with Docker Compose

Stop the manual processes (and `docker rm -f taskboard-postgres`), then:

```bash
docker compose up -d --build
docker compose ps
docker compose logs backend
```

The images are built and Postgres becomes **healthy** before the backend starts. The backend runs the Alembic migration, then starts Uvicorn.

![docker compose up](screenshots/05-docker-compose-up.png)

### Troubleshooting: backend exited on the first `docker compose up`

With the original `depends_on: [postgres]`, Compose only waits for the Postgres **container to start**, not for the **database to accept connections**. The backend ran `alembic upgrade head` too early and exited with `Connection refused`:

![backend starts before postgres](screenshots/06-issue-backend-starts-before-postgres.png)

**Fix** in `docker-compose.yml`: add a `pg_isready` healthcheck to Postgres and make the backend wait for it.

```yaml
  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U taskboard -d taskboard"]
      interval: 5s
      timeout: 3s
      retries: 10

  backend:
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
```

---

## Part 3 – Test the backend APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/`, `/health`, `/ready` | service info, liveness, readiness (DB check) |
| GET | `/api/tasks` | list tasks |
| POST | `/api/tasks` | create a task |
| GET | `/api/tasks/{id}` | get one task |
| PUT | `/api/tasks/{id}` | update a task |
| DELETE | `/api/tasks/{id}` | delete a task |
| GET | `/api/tasks/stats` | counts by status |

```bash
curl -s localhost:8000/health
curl -s -X POST localhost:8000/api/tasks -H 'Content-Type: application/json' \
  -d '{"title":"Write Dockerfiles","priority":"HIGH","assignee":"Pranay","status":"DONE"}'
curl -s localhost:8000/api/tasks/2
curl -s -X PUT localhost:8000/api/tasks/2 -H 'Content-Type: application/json' -d '{"status":"IN_PROGRESS"}'
curl -s -X DELETE localhost:8000/api/tasks/4          # 204
curl -s localhost:8000/api/tasks/4                    # 404 Task not found
curl -s localhost:8000/api/tasks/stats
curl -s localhost:3000/api/tasks                      # same API through the frontend's nginx proxy
```

The screenshot covers create, read, update, delete, 404 handling, input validation (empty title rejected), stats, and the nginx `/api` proxy:

![backend API tests](screenshots/07-backend-api-tests.png)

## Part 4 – Test the application in the browser

http://localhost:3000 runs from the Docker Compose stack and shows the tasks created through the API, with stats updated:

![app via docker compose](screenshots/08-app-browser-compose.png)

Interactive API docs (Swagger UI) at http://localhost:8000/docs:

![swagger](screenshots/09-swagger-api-docs.png)

---

## Changes made to the starter code

| File | Change | Why |
|---|---|---|
| `docker-compose.yml` | Postgres healthcheck + `condition: service_healthy` + `restart: unless-stopped` | the backend crashed when it started before the DB was ready (see troubleshooting) |
| `backend/tests/test_api.py` | Create tables before the tests run | `TestClient(app)` without `with` never fires the startup event, so `test_create_task_validation` failed with `no such table: tasks` |
| `frontend/vite.config.js` | Dev proxy `/api` → `localhost:8000` (was `8080`) | the backend listens on 8000, so the manual dev run couldn't reach the API |
| `.gitignore` | ignore `.venv/`, `__pycache__/`, `*.db` | keep local build and test files out of git |

## Cleanup

```bash
docker compose down        # add -v to also delete the database volume
```
