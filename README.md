# Cybersecurity Analytics Dashboard

Django dashboard for displaying the critical results from the supplied cybersecurity analysis notebook.

## Structure

- `cyberdashboard/urls.py` — project URL routing
- `dashboard/apps.py` — Django app configuration
- `dashboard/urls.py` — dashboard/API routes
- `dashboard/views.py` — CSV statistics + notebook model results
- `dashboard/templates/dashboard/index.html` — dashboard UI
- `dashboard/static/dashboard/css/style.css` — styling
- `dashboard/static/dashboard/js/dashboard.js` — Chart.js rendering
- `data/cybersecurity_attacks.csv` — supplied dataset

## Run

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
django-admin startproject temp .  # do not run this if you already have the included project files
python manage.py migrate
python manage.py runserver
```

The included files are the requested Django app/project pieces. If starting from an existing Django project,
copy `dashboard/` and merge the URL patterns into your existing project `urls.py`.

Note: the supplied request asked for `app.py`; Django convention is `apps.py`, so the file is named `dashboard/apps.py`.
"# Arkar-zin-moe" 
