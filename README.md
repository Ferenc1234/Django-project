# Filament Inventory (Django)

This project is a Django web application for managing 3D printer filament inventory.

It lets you store filament products, assign them to manufacturers, and track physical spools with current remaining weight and status.

## What This Project Is About

The app models a small warehouse/catalog workflow for 3D printing materials:

- save filament products (material, colors, color mode)
- track one or more physical spools per filament
- monitor remaining stock in grams and percentages
- filter and browse all inventory on a catalog page
- open a dedicated detail page for each filament
- edit data from both Django admin and custom app forms

## Data Model

Main related objects:

- Manufacturer
- Filament (belongs to a Manufacturer)
- Spool (belongs to a Filament)

So the requirement of at least 3 connected data entities is fulfilled by:
Manufacturer -> Filament -> Spool.

## Main Pages

- Home page: inventory catalog with filters and quick stock usage
- Filament detail page: separate page with detailed filament + spool info
- Login page: authentication for editing operations
- Admin page: full Django administration

## How It Works

1. The catalog reads all filaments and related spools from SQLite.
2. Remaining stock is computed per spool and displayed as progress.
3. "Quick usage" subtracts entered grams from the most suitable spool.
4. When remaining weight reaches 0, the spool is removed.
5. Logged-in users can add/edit filaments and spools.

## Run The Project

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Apply migrations:

```bash
python manage.py migrate
```

3. Start the server:

```bash
python manage.py runserver
```

4. Open:

- App: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

## Admin Login

Use this superuser account:

- Username: admin
- Password: Admin123

(For school/demo use only. Change password if deploying anywhere else.)

## Tech Stack

- Python
- Django
- SQLite3

## Repository Notes

- Dependencies are listed in requirements.txt
- Git is used for local and remote version history (GitHub)
- .gitignore excludes environment/cache/database/media artifacts for development
