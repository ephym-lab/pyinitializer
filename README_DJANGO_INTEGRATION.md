# Django Project Generation Integration

This document explains how the Python Initializr backend handles Django project generation. This is intended for frontend developers and backend maintainers to understand the API contract and the underlying process.

## 1. API Selection

To trigger a Django project generation, the frontend must send a `POST` request to the `/api/v1/projects/zip` endpoint with the following configuration:

### Request Body (JSON)
- `framework`: Must be set to `"django"`.
- `project_type`: Must be set to `"web-api"`.
- `django_apps`: A list of strings representing the names of the Django applications to be created (e.g., `["users", "profiles", "api"]`).
- `dependencies`: It is **highly recommended** to include `"django"` in the dependencies list. This ensures `django-admin` is available in the generated virtual environment.

### Example Request
```json
{
  "project_name": "my-awesome-django-app",
  "package_manager": "pip",
  "python_version": "3.11",
  "project_type": "web-api",
  "framework": "django",
  "dependencies": ["django", "djangorestframework"],
  "django_apps": ["core", "api"]
}
```

## 2. Backend Workflow

When the backend receives a Django configuration, it follows these steps:

1.  **Scaffold Baseline**: The `project_builder` creates a baseline structure and includes a `README_DJANGO.md` in the root of the generated project.
2.  **Virtual Environment**: A virtual environment is created in the temp directory.
3.  **Dependency Installation**: All listed dependencies (including `django`) are installed into the venv.
4.  **Django Initialization**:
    -   The backend runs `python -m django startproject <module_name> .` to initialize the Django project in the root directory.
    -   For each app in `django_apps`, it runs `python manage.py startapp <app_name>`.
5.  **Zipping**: The entire initialized project structure is zipped and streamed back to the user.

## 3. Important Notes for Frontend

-   **App Validation**: App names should be valid Python identifiers (lowercase, no special characters except underscores, cannot start with a number).
-   **Initialization Time**: Because Django initialization involves installing packages and running multiple shell commands, the response time might be slightly longer than for other frameworks. Ensure the frontend handles a reasonable timeout.
-   **Venv Size**: If the resulting virtual environment exceeds the server's limit (default 50MB), it will be excluded from the ZIP, and a `setup.sh` script will be provided instead.

## 4. Generated Project Structure

The user will receive a standard Django layout:
```text
my_awesome_django_app/
├── manage.py
├── my_awesome_django_app/
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── core/
│   ├── migrations/
│   ├── apps.py
│   └── ...
├── api/
│   └── ...
└── README_DJANGO.md
```
