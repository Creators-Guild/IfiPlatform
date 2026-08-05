# IfiPlatform
Student platform for IFI-UIO by students for students

## About
Goals:
- One place find information for IFI-students
- One place to find IFI-tools (ex. Peoply, Trix, IFI Rom etc.)
- A growing student library with study-resources made by IFI-students with main focus on IFI-subjects (based on IFI curriculum) and reuse
- A collection of study tools to build and represent study-resources (ex. flashcards, multiple choice, mock exam etc.)

Note: the site is bilingual (Norwegian Bokmål + English) via wagtail-localize — new content pages generally need both locales.

## Tools and Languages
1. Framework: Django + Wagtail (CMS layer — pages, articles, categories, admin editing)
2. Languages: Python, HTML and CSS
3. Key dependencies: wagtail-localize (nb/en translation)
4. Requirements:
    - Python
      - Minimum 3.12
      - Supported and tested on 3.12, 3.13, 3.14
    - SQLite (default, via Django)

## Setup
> **A note on file paths below:** "repo root" means the top-level folder you get from cloning (likely named `IfiPlatform`). 

>Steps also reference the `ifiplatform/` subdirectory inside it (likely named `ifiplatform`, lowercase (*not to be confused with `ifiplatform/ifiplatform_project/`, which is just the Django settings package*) — that's where manage.py, `.env` and all the Django apps actually live. Steps say which one they're relative to.

### Set up Virtual Environment
#### Windows (PowerShell)
```bash
py -m venv venv
venv\Scripts\Activate.ps1
```
#### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```
#### Or through Visual Studio Code
Run this command from the Command Palette:
```bash
Python: Create Environment
```
### Install dependencies
Run from the repo root:
```bash
pip install -r requirements.txt
```

### Move into the ifiplatform/ folder
manage.py, `.env` and all the Django apps live in `ifiplatform/`. Every command from here on assumes you're inside it:
```bash
cd ifiplatform
```

### Create .env for Secrets
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Generate local Secret key and copy generated key and replace 'your-secret-key-here' inside .env with said key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
*Editing remaining if necessary. For just development, add SecretKey and leave Debug=True. Ignore the rest*

### Run Migrations
```bash
py manage.py migrate
```

### Fill database with dummy data(recommended)
```bash
py manage.py seed_dev_data
```
Fills your local database with a dummy article tree (index pages, categories, a test article, a test student union and a test tool) so you're not starting from a blank site. Safe to re-run — it skips anything that already exists instead of duplicating it.

### Run website on localhost
```bash
py manage.py runserver
```
Once running, open your browser and go to:
```
http://localhost:8000
```

### Often used commands and actions
#### If you change a model (i.e. need a new migration)
```bash
py manage.py makemigrations
py manage.py migrate
```
#### To create superuser/admin user
```bash
py manage.py createsuperuser
```
Fill out the terminal's questions
#### Running tests
```bash
py manage.py test
```
CI runs this on every push/PR (`.github/workflows/django.yml`) across Python 3.12–3.14, so it's worth running locally before opening a PR.
#### If you change translatable text (`{% trans %}` / `_(...)`)
Update the `.po` files with the new/changed strings:
```bash
py manage.py makemessages -l nb -l en
```
Then compile them so Django actually picks up the changes:
```bash
py manage.py compilemessages
```
If that fails because `msgfmt` (part of GNU gettext) isn't installed — common on Windows, and it needs admin rights to install via `choco install gettext` — use this project's pure-Python fallback instead:
```bash
py manage.py compile_translations
```
Same effect, no system dependency. Only compiles this project's own `.po` files (`ifiplatform/locale/`), not any third-party package's.
#### Log in on admin interface or wagtail-admin interface
Log in via a superuser you have created.
```
http://localhost:8000/admin
```
Django's own admin — user accounts, permissions, raw model tables.
```
http://localhost:8000/wagtail-admin
```
Wagtail's CMS admin — this is where you edit articles, categories and their index pages.
- Highly recommend filling the database with seed data first (see above) so you can see the real page structure.

## Project Structure
```
IfiPlatform/
├── requirements.txt
├── docs/                     # architecture & design references
├── CONTRIBUTING.md
├── LICENSE
└── ifiplatform/              # the actual Django project
    ├── manage.py
    ├── .env                  # secrets
    ├── ifiplatform_project/  # settings, urls
    ├── ifi_home_app/         # articles, categories, homepage
    ├── study_app/
    ├── account_app/
    ├── yourpage_app/
    ├── locale/               # i18n .po/.mo files
    └── static/ & templates/
```

## Architecture
- Feature concept map: see [docs/architecture/eraser_links.md](docs/architecture/eraser_links.md)
- UI/design references: see [docs/design/figma_links.md](docs/design/figma_links.md)

## Tutorials
Check out [TUTORIALS.md](TUTORIALS.md) for more about Django Framework and other dependencies used in this project.

## Contributing
We welcome contributions mainly from IFI students(with certain exceptions)! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to open issues (bug/feature/task reports, with examples)
- How to submit pull requests
- Code style expectations (Black/Pylint)
- The different contributor roles in this project
- Precisely who can contribute

## License
This project is licensed under the [MIT License](LICENSE).
