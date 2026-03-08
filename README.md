# Python Initializr — Backend API Reference

FastAPI backend for Python Initializr.  
**Base URL (local dev):** `http://localhost:8000`  
**Interactive docs:** `http://localhost:8000/docs`

---

## Running locally

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Set the optional environment variable to control venv size limit:

```bash
export MAX_VENV_SIZE_MB=50   # default: 50
```

---

## CORS

The server allows requests from `http://localhost:3000` (Next.js dev server) and `http://127.0.0.1:3000` out of the box. No extra config needed for local development.

---

## Data model

All `POST` endpoints accept a `ProjectConfig` JSON body:

```ts
// TypeScript type for your frontend
type PackageManager = "pip" | "uv" | "conda";
type PythonVersion  = "3.10" | "3.11" | "3.12" | "3.13";
type ProjectType    = "library" | "cli" | "web-api" | "data-science";
type Framework      = "fastapi" | "flask" | "django";

interface ProjectConfig {
  project_name:    string;          // letters,   digits, hyphens, underscores only
  package_manager: PackageManager;
  python_version:  PythonVersion;
  project_type:    ProjectType;
  framework?:      Framework;       // only valid when project_type === "web-api"
  dependencies:    string[];        // PyPI package names
}
```

**Validation rules:**
- `project_name` — only `[a-zA-Z0-9_\-]`, max 80 chars
- `framework` — must be `null`/omitted unless `project_type === "web-api"`

---

## Endpoints

### `GET /search/packages`

Search the cached PyPI index for autocomplete suggestions.

**Query params:**

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `q`   | string | ✅ | — | Search query (min 1 char) |
| `limit` | integer | ❌ | `20` | Max results (1–100) |

**Example:**

```ts
const res = await fetch("http://localhost:8000/search/packages?q=fast&limit=10");
const { results, index_loaded } = await res.json();
// results: ["fastapi", "fastapi2cli", ...]
// index_loaded: true (false for a few seconds on cold start)
```

**Response:**

```json
{
  "query": "fast",
  "results": ["fastapi", "fastapi2cli", "fastapi-admin", "..."],
  "index_loaded": true
}
```

> **Note:** The PyPI index (~750k packages) loads in the background on startup. When `index_loaded` is `false`, return an empty dropdown and retry on the next keystroke.

---

### `POST /preview`

Returns the project file tree as JSON. Call this on every config change to power the live preview panel.

**Request body:** `ProjectConfig`

**Example:**

```ts
const res = await fetch("http://localhost:8000/preview", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    project_name: "my-api",
    package_manager: "uv",
    python_version: "3.12",
    project_type: "web-api",
    framework: "fastapi",
    dependencies: ["fastapi", "sqlalchemy"],
  }),
});
const data = await res.json();
```

**Response:**

```json
{
  "project_name": "my-api",
  "total_files": 6,
  "files": [
    { "path": "tests",              "type": "directory" },
    { "path": ".gitignore",         "type": "file", "content": "..." },
    { "path": ".python-version",    "type": "file", "content": "3.12\n" },
    { "path": "README.md",          "type": "file", "content": "..." },
    { "path": "main.py",            "type": "file", "content": "..." },
    { "path": "pyproject.toml",     "type": "file", "content": "..." },
    { "path": "tests/test_main.py", "type": "file", "content": "..." }
  ]
}
```

**File node shape:**

```ts
interface FileNode {
  path:     string;           // relative path, e.g. "src/my_api/__init__.py"
  type:     "file" | "directory";
  content?: string;           // present only when type === "file"
}
```

---

### `POST /generate/zip`

Scaffolds the project, creates a virtualenv, installs dependencies, and returns a downloadable ZIP.

**Request body:** `ProjectConfig`

**Response:** Binary ZIP (`application/zip`)

**Important response headers:**

| Header | Value | Meaning |
|--------|-------|---------|
| `Content-Disposition` | `attachment; filename="<project_name>.zip"` | Triggers browser download |
| `X-Venv-Excluded` | `"true"` | Present only when venv was excluded (see below). A `setup.sh` is included in the ZIP instead. |

**When is the venv excluded?**
- The venv size exceeds `MAX_VENV_SIZE_MB` (default 50 MB), **or**
- The target Python version isn't installed on the server

**Example — trigger download + handle venv warning:**

```ts
const res = await fetch("http://localhost:8000/generate/zip", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(config),
});

if (!res.ok) {
  const err = await res.json();
  throw new Error(err.detail);
}

// Show warning if venv was excluded
const venvExcluded = res.headers.get("X-Venv-Excluded") === "true";

// Trigger download
const blob = await res.blob();
const url  = URL.createObjectURL(blob);
const a    = document.createElement("a");
a.href     = url;
a.download = `${config.project_name}.zip`;
a.click();
URL.revokeObjectURL(url);
```

> **CORS note:** `X-Venv-Excluded` is already in `expose_headers` on the backend so it is readable from browser JS.

---

### `POST /generate/script`

Returns a bash setup script tailored to the chosen package manager.

**Request body:** `ProjectConfig`

**Response:** `text/plain`, `Content-Disposition: attachment; filename="setup_<project_name>.sh"`

**Example — copy to clipboard or download:**

```ts
const res = await fetch("http://localhost:8000/generate/script", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(config),
});

const script = await res.text();

// Option A: copy to clipboard
await navigator.clipboard.writeText(script);

// Option B: download as file
const blob = new Blob([script], { type: "text/plain" });
const url  = URL.createObjectURL(blob);
const a    = document.createElement("a");
a.href     = url;
a.download = `setup_${config.project_name}.sh`;
a.click();
URL.revokeObjectURL(url);
```

---

## Error handling

All endpoints return standard problem JSON on failure:

```json
{ "detail": "Human-readable error message" }
```

| Status | When |
|--------|------|
| `422 Unprocessable Entity` | Invalid `ProjectConfig` (bad `project_name`, `framework` set on non-web-api, etc.) |
| `500 Internal Server Error` | ZIP/script generation failure |

```ts
if (!res.ok) {
  const { detail } = await res.json();
  // show `detail` to the user
}
```

---

## Shareable URL integration

The backend is completely stateless. Encode the entire config as URL query params in the frontend:

```ts
// Next.js example — encode config into URL on every change
import { useRouter, useSearchParams } from "next/navigation";

// Write
const params = new URLSearchParams({
  name: config.project_name,
  pm:   config.package_manager,
  py:   config.python_version,
  type: config.project_type,
  fw:   config.framework ?? "",
  deps: config.dependencies.join(","),
});
router.push(`/?${params.toString()}`, { scroll: false });

// Read on page load
const sp = useSearchParams();
const initialConfig: ProjectConfig = {
  project_name:    sp.get("name")  ?? "my-project",
  package_manager: (sp.get("pm")   ?? "pip") as PackageManager,
  python_version:  (sp.get("py")   ?? "3.12") as PythonVersion,
  project_type:    (sp.get("type") ?? "library") as ProjectType,
  framework:       (sp.get("fw") || undefined) as Framework | undefined,
  dependencies:    sp.get("deps")?.split(",").filter(Boolean) ?? [],
};
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_VENV_SIZE_MB` | `50` | Max venv size before it's excluded from ZIP |
| `NEXT_PUBLIC_API_URL` | *(set in frontend .env)* | API base URL consumed by Next.js |

---

## Generated file structure reference

| File | library | cli | web-api | data-science |
|------|:-------:|:---:|:-------:|:-----------:|
| `.gitignore` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `.python-version` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `README.md` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `requirements.txt` (pip/conda) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `pyproject.toml` (uv/poetry/pipenv) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `main.py` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `src/<name>/__init__.py` | ✅ | — | — | ✅ | ✅ |
| `tests/test_<name>.py` | ✅ | — | — | — | — |
| `tests/test_main.py` | — | ✅ | ✅ | — | — |
| `notebooks/.gitkeep` | — | — | — | ✅ | ✅ |
| `data/.gitkeep` | — | — | — | ✅ | ✅ |
| `setup.sh` *(if venv excluded)* | ✅ | ✅ | ✅ | ✅ | ✅ |
