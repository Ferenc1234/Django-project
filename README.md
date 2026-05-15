# Django-project

Default clean Django project with:

- Hello World homepage at `/`
- Integrated SQLite database
- File upload form that saves uploaded files via the database

## Run locally

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Then open http://127.0.0.1:8000/
