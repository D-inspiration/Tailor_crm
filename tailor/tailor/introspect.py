#!/usr/bin/env python
"""
Tailor CRM - Complete Project Introspection Script
Run with: python manage.py shell < introspect.py
Or: python manage.py shell
>>> exec(open('introspect.py').read())
"""

import os
import sys
import inspect
import importlib
import pkgutil
from pathlib import Path
from django.apps import apps
from django.db import models
from django import forms
from django.views import View
from django.urls import URLPattern, URLResolver

def print_header(title, char="="):
    """Print a formatted header."""
    print(f"\n{char * 70}")
    print(f"  {title}")
    print(f"{char * 70}")

def print_subheader(title, char="-"):
    """Print a formatted subheader."""
    print(f"\n{char * 50}")
    print(f"  {title}")
    print(f"{char * 50}")

def get_source_info(obj):
    """Get file path and line number of an object."""
    try:
        file_path = inspect.getfile(obj)
        line_no = inspect.getsourcelines(obj)[1]
        return f"{file_path}:{line_no}"
    except (TypeError, OSError):
        return "built-in"

def analyze_model(model):
    """Analyze a Django model and return detailed info."""
    info = {
        'name': model.__name__,
        'module': model.__module__,
        'source': get_source_info(model),
        'db_table': model._meta.db_table,
        'verbose_name': model._meta.verbose_name,
        'verbose_name_plural': model._meta.verbose_name_plural,
        'fields': [],
        'methods': [],
        'properties': [],
        'meta': {},
        'managers': [],
    }

    # Fields
    for field in model._meta.get_fields():
        field_info = {
            'name': field.name,
            'type': field.__class__.__name__,
            'verbose_name': getattr(field, 'verbose_name', ''),
            'null': getattr(field, 'null', False),
            'blank': getattr(field, 'blank', False),
            'default': getattr(field, 'default', None),
            'help_text': getattr(field, 'help_text', ''),
        }
        if hasattr(field, 'max_length'):
            field_info['max_length'] = field.max_length
        if hasattr(field, 'choices') and field.choices:
            field_info['choices'] = field.choices
        if hasattr(field, 'related_model') and field.related_model:
            field_info['related_model'] = field.related_model.__name__
        info['fields'].append(field_info)

    # Methods and properties
    for name in dir(model):
        if name.startswith('_'):
            continue
        attr = getattr(model, name)
        if callable(attr) and not isinstance(attr, models.Manager):
            if isinstance(attr, property):
                info['properties'].append({
                    'name': name,
                    'source': get_source_info(attr.fget) if hasattr(attr, 'fget') else 'N/A'
                })
            else:
                try:
                    sig = inspect.signature(attr)
                    info['methods'].append({
                        'name': name,
                        'signature': str(sig),
                        'source': get_source_info(attr)
                    })
                except (ValueError, TypeError):
                    pass
        elif isinstance(attr, models.Manager):
            info['managers'].append({
                'name': name,
                'type': attr.__class__.__name__
            })

    # Meta options
    meta_attrs = ['ordering', 'indexes', 'unique_together', 'verbose_name', 
                  'verbose_name_plural', 'db_table']
    for attr in meta_attrs:
        val = getattr(model._meta, attr, None)
        if val:
            info['meta'][attr] = val

    return info

def analyze_view_func(func):
    """Analyze a view function."""
    info = {
        'name': func.__name__,
        'module': func.__module__,
        'source': get_source_info(func),
        'docstring': inspect.getdoc(func) or 'No docstring',
    }
    try:
        info['signature'] = str(inspect.signature(func))
    except (ValueError, TypeError):
        info['signature'] = 'N/A'

    # Check for decorators
    info['decorators'] = []
    if hasattr(func, '__wrapped__'):
        info['decorators'].append('wrapped')

    return info

def analyze_form(form_class):
    """Analyze a Django form."""
    info = {
        'name': form_class.__name__,
        'module': form_class.__module__,
        'source': get_source_info(form_class),
        'fields': [],
        'methods': [],
        'meta': {},
    }

    # Form fields
    if hasattr(form_class, 'base_fields'):
        for name, field in form_class.base_fields.items():
            info['fields'].append({
                'name': name,
                'type': field.__class__.__name__,
                'required': field.required,
                'label': field.label or name,
                'help_text': str(field.help_text) if field.help_text else '',
            })

    # Methods
    for name in dir(form_class):
        if name.startswith('_') or name in ['base_fields', 'declared_fields']:
            continue
        attr = getattr(form_class, name)
        if callable(attr):
            try:
                sig = inspect.signature(attr)
                info['methods'].append({
                    'name': name,
                    'signature': str(sig),
                })
            except (ValueError, TypeError):
                pass

    return info

def analyze_url_pattern(pattern, prefix=''):
    """Analyze URL patterns recursively."""
    urls = []
    if isinstance(pattern, URLResolver):
        for p in pattern.url_patterns:
            urls.extend(analyze_url_pattern(p, prefix + str(pattern.pattern)))
    elif isinstance(pattern, URLPattern):
        view = pattern.callback
        view_name = getattr(pattern, 'name', 'unnamed')
        view_type = 'function'
        if inspect.isclass(view) and issubclass(view, View):
            view_type = 'class-based'
        urls.append({
            'pattern': prefix + str(pattern.pattern),
            'name': view_name,
            'view': view.__name__ if hasattr(view, '__name__') else str(view),
            'view_type': view_type,
            'module': getattr(view, '__module__', 'N/A'),
        })
    return urls

# ============================================================
# MAIN INTROSPECTION
# ============================================================

print_header("TAILOR CRM - COMPLETE PROJECT INTROSPECTION")
print(f"Project: tailor_crm")
print(f"Python: {sys.version}")
print(f"Django: {importlib.import_module('django').__version__}")

# 1. MODELS
# ============================================================
print_header("1. DJANGO MODELS", "=")

for app_config in apps.get_app_configs():
    app_name = app_config.label
    if app_name in ['admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles']:
        continue

    print_subheader(f"App: {app_name}")

    for model in app_config.get_models():
        info = analyze_model(model)
        print(f"\n  Model: {info['name']}")
        print(f"  Source: {info['source']}")
        print(f"  DB Table: {info['db_table']}")

        if info['meta']:
            print(f"  Meta: {info['meta']}")

        print(f"  Fields:")
        for field in info['fields']:
            choices_str = ''
            if 'choices' in field:
                choices_str = f" choices={field['choices']}"
            print(f"    - {field['name']}: {field['type']}" 
                  f"{' [PK]' if field.get('primary_key') else ''}"
                  f"{' [FK->' + field.get('related_model', '') + ']' if 'related_model' in field else ''}"
                  f"{' [null]' if field['null'] else ''}"
                  f"{' [blank]' if field['blank'] else ''}"
                  f"{choices_str}")

        if info['managers']:
            print(f"  Managers:")
            for mgr in info['managers']:
                print(f"    - {mgr['name']}: {mgr['type']}")

        if info['properties']:
            print(f"  Properties:")
            for prop in info['properties']:
                print(f"    - {prop['name']}")

        if info['methods']:
            print(f"  Methods:")
            for method in info['methods']:
                print(f"    - {method['name']}{method['signature']}")

# 2. VIEWS
# ============================================================
print_header("2. VIEWS (Functions & Classes)", "=")

view_modules = []
for app_config in apps.get_app_configs():
    app_name = app_config.label
    if app_name in ['admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles']:
        continue
    try:
        views_module = importlib.import_module(f'{app_name}.views')
        view_modules.append((app_name, views_module))
    except ImportError:
        pass

for app_name, module in view_modules:
    print_subheader(f"App: {app_name}")

    for name, obj in inspect.getmembers(module):
        if name.startswith('_'):
            continue

        if inspect.isfunction(obj):
            info = analyze_view_func(obj)
            print(f"\n  Function: {info['name']}{info['signature']}")
            print(f"  Source: {info['source']}")
            print(f"  Doc: {info['docstring'][:80]}..." if len(info['docstring']) > 80 else f"  Doc: {info['docstring']}")

        elif inspect.isclass(obj) and issubclass(obj, View):
            print(f"\n  Class: {obj.__name__} (Class-Based View)")
            print(f"  Source: {get_source_info(obj)}")
            for method_name, method in inspect.getmembers(obj, predicate=inspect.isfunction):
                if not method_name.startswith('_') or method_name in ['get', 'post', 'put', 'delete', 'patch']:
                    try:
                        sig = inspect.signature(method)
                        print(f"    Method: {method_name}{sig}")
                    except (ValueError, TypeError):
                        print(f"    Method: {method_name}")

# 3. FORMS
# ============================================================
print_header("3. FORMS", "=")

form_modules = []
for app_config in apps.get_app_configs():
    app_name = app_config.label
    if app_name in ['admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles']:
        continue
    try:
        forms_module = importlib.import_module(f'{app_name}.forms')
        form_modules.append((app_name, forms_module))
    except ImportError:
        pass

for app_name, module in form_modules:
    print_subheader(f"App: {app_name}")

    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, forms.Form):
            info = analyze_form(obj)
            print(f"\n  Form: {info['name']}")
            print(f"  Source: {info['source']}")
            print(f"  Fields:")
            for field in info['fields']:
                print(f"    - {field['name']}: {field['type']}"
                      f"{' [required]' if field['required'] else ' [optional]'}")
            if info['methods']:
                print(f"  Methods:")
                for method in info['methods']:
                    print(f"    - {method['name']}{method['signature']}")

# 4. URL PATTERNS
# ============================================================
print_header("4. URL ROUTING", "=")

from django.urls import get_resolver
resolver = get_resolver()

all_urls = []
for pattern in resolver.url_patterns:
    all_urls.extend(analyze_url_pattern(pattern))

# Group by app
from collections import defaultdict
urls_by_app = defaultdict(list)
for url in all_urls:
    module = url['module']
    app_name = module.split('.')[0] if '.' in module else module
    urls_by_app[app_name].append(url)

for app_name, urls in sorted(urls_by_app.items()):
    print_subheader(f"App: {app_name}")
    for url in urls:
        print(f"  {url['pattern']:40s} -> {url['view']:30s} [{url['view_type']}] name='{url['name']}'")

# 5. SETTINGS
# ============================================================
print_header("5. PROJECT SETTINGS", "=")

from django.conf import settings

settings_to_show = [
    'DEBUG', 'ALLOWED_HOSTS', 'DATABASES', 'INSTALLED_APPS',
    'MIDDLEWARE', 'LANGUAGE_CODE', 'TIME_ZONE', 'STATIC_URL',
    'MEDIA_URL', 'LOGIN_REDIRECT_URL', 'LOGOUT_REDIRECT_URL',
]

for setting in settings_to_show:
    val = getattr(settings, setting, 'NOT SET')
    if setting == 'DATABASES':
        print(f"  {setting}:")
        for db_name, db_config in val.items():
            engine = db_config.get('ENGINE', 'N/A')
            name = db_config.get('NAME', 'N/A')
            print(f"    {db_name}: {engine} -> {name}")
    elif setting == 'INSTALLED_APPS':
        print(f"  {setting}:")
        for app in val:
            print(f"    - {app}")
    elif setting == 'MIDDLEWARE':
        print(f"  {setting}:")
        for mw in val:
            print(f"    - {mw}")
    else:
        print(f"  {setting}: {val}")

# 6. SIGNALS
# ============================================================
print_header("6. SIGNALS & RECEIVERS", "=")

for app_config in apps.get_app_configs():
    app_name = app_config.label
    if app_name in ['admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles']:
        continue
    try:
        signals_module = importlib.import_module(f'{app_name}.signals')
        print_subheader(f"App: {app_name}")
        for name, obj in inspect.getmembers(signals_module):
            if inspect.isfunction(obj) and not name.startswith('_'):
                print(f"  Receiver: {name}()")
                print(f"    Source: {get_source_info(obj)}")
                print(f"    Doc: {inspect.getdoc(obj) or 'No docstring'}")
    except ImportError:
        pass

# 7. MANAGEMENT COMMANDS
# ============================================================
print_header("7. MANAGEMENT COMMANDS", "=")

from django.core.management import get_commands
commands = get_commands()
project_commands = {k: v for k, v in commands.items() if v in ['customers', 'orders']}
if project_commands:
    for cmd, app in sorted(project_commands.items()):
        print(f"  {cmd:20s} (from {app})")
else:
    print("  No custom management commands found.")

# 8. SUMMARY
# ============================================================
print_header("8. PROJECT SUMMARY", "=")

total_models = 0
total_views = 0
total_forms = 0

for app_config in apps.get_app_configs():
    app_name = app_config.label
    if app_name in ['admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles']:
        continue

    model_count = len(app_config.get_models())
    total_models += model_count

    try:
        views_module = importlib.import_module(f'{app_name}.views')
        view_count = len([n for n, o in inspect.getmembers(views_module) 
                         if inspect.isfunction(o) or (inspect.isclass(o) and issubclass(o, View))])
        total_views += view_count
    except ImportError:
        pass

    try:
        forms_module = importlib.import_module(f'{app_name}.forms')
        form_count = len([n for n, o in inspect.getmembers(forms_module) 
                         if inspect.isclass(o) and issubclass(o, forms.Form)])
        total_forms += form_count
    except ImportError:
        pass

print(f"  Total Custom Apps: {len([a for a in apps.get_app_configs() if a.label not in ['admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles']])}")
print(f"  Total Models: {total_models}")
print(f"  Total Views: {total_views}")
print(f"  Total Forms: {total_forms}")
print(f"  Total URL Routes: {len(all_urls)}")

print("\n" + "=" * 70)
print("  INTROSPECTION COMPLETE")
print("=" * 70 + "\n")
