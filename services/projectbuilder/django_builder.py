from __future__ import annotations
import textwrap
from .base import ProjectBuilderBase, FileTree

class DjangoBuilder(ProjectBuilderBase):
    """Django project scavenger."""

    def build(self, tree: FileTree) -> None:
        n = self.config.project_name
        mn = self.config.module_name

        # manage.py
        tree["manage.py"] = textwrap.dedent(f"""\
            #!/usr/bin/env python
            import os
            import sys

            def main():
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{mn}.settings')
                try:
                    from django.core.management import execute_from_command_line
                except ImportError as exc:
                    raise ImportError(
                        "Couldn't import Django. Are you sure it's installed and "
                        "available on your PYTHONPATH environment variable? Did you "
                        "forget to activate a virtual environment?"
                    ) from exc
                execute_from_command_line(sys.argv)

            if __name__ == '__main__':
                main()
        """)

        # Project folder
        tree[f"{mn}/__init__.py"] = ""
        tree[f"{mn}/settings.py"] = textwrap.dedent(f"""\
            from pathlib import Path

            BASE_DIR = Path(__file__).resolve().parent.parent
            SECRET_KEY = 'django-insecure-changeme-in-production'
            DEBUG = True
            ALLOWED_HOSTS = []

            INSTALLED_APPS = [
                'django.contrib.admin',
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
                'django.contrib.staticfiles',
            ]
            # Add requested apps
            {chr(10).join(f"INSTALLED_APPS.append('{app}')" for app in self.config.django_apps)}

            MIDDLEWARE = [
                'django.middleware.security.SecurityMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.common.CommonMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
                'django.middleware.clickjacking.XFrameOptionsMiddleware',
            ]

            ROOT_URLCONF = '{mn}.urls'

            TEMPLATES = [
                {{
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                    'DIRS': [],
                    'APP_DIRS': True,
                    'OPTIONS': {{
                        'context_processors': [
                            'django.template.context_processors.debug',
                            'django.template.context_processors.request',
                            'django.contrib.auth.context_processors.auth',
                            'django.contrib.messages.context_processors.messages',
                        ],
                    }},
                }},
            ]

            WSGI_APPLICATION = '{mn}.wsgi.application'

            DATABASES = {{
                'default': {{
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': BASE_DIR / 'db.sqlite3',
                }}
            }}

            AUTH_PASSWORD_VALIDATORS = [
                {{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}},
                {{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}},
                {{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}},
                {{'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}},
            ]

            LANGUAGE_CODE = 'en-us'
            TIME_ZONE = 'UTC'
            USE_I18N = True
            USE_TZ = True
            STATIC_URL = 'static/'
            DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
        """)

        tree[f"{mn}/urls.py"] = textwrap.dedent(f"""\
            from django.contrib import admin
            from django.urls import path

            urlpatterns = [
                path('admin/', admin.site.urls),
            ]
        """)

        tree[f"{mn}/wsgi.py"] = textwrap.dedent(f"""\
            import os
            from django.core.wsgi import get_wsgi_application
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{mn}.settings')
            application = get_wsgi_application()
        """)

        tree[f"{mn}/asgi.py"] = textwrap.dedent(f"""\
            import os
            from django.core.asgi import get_asgi_application
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{mn}.settings')
            application = get_asgi_application()
        """)

        # App folders
        for app in self.config.django_apps:
            tree[f"{app}/__init__.py"] = ""
            tree[f"{app}/admin.py"] = "from django.contrib import admin\n"
            tree[f"{app}/apps.py"] = textwrap.dedent(f"""\
                from django.apps import AppConfig

                class {app.capitalize()}Config(AppConfig):
                    default_auto_field = 'django.db.models.BigAutoField'
                    name = '{app}'
            """)
            tree[f"{app}/models.py"] = "from django.db import models\n"
            tree[f"{app}/tests.py"] = "from django.test import TestCase\n"
            tree[f"{app}/views.py"] = "from django.shortcuts import render\n"
            tree[f"{app}/migrations/__init__.py"] = ""
