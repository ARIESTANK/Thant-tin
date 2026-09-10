# Myanmar University Enrollment Django Dashboard

## Run

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python manage.py runserver
```

Open http://127.0.0.1:8000/

The CSV is already placed in `data/`.

## Important

The dashboard trains the models on the first API request and caches the result in memory.
Use the refresh button to reload the dashboard; restart Django after changing the dataset.

Files requested:
- `university_dashboard/urls.py`
- `dashboard_app/app.py`
- `dashboard_app/views.py`
- `dashboard_app/templates/dashboard.html`
- `dashboard_app/static/css/dashboard.css`
- `dashboard_app/static/js/dashboard.js`
