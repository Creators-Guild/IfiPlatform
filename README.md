# IfiPlatform
Student platform for IFI-UIO by students for students

## About
Goals:
- One place find information for IFI-students
- One place to find IFI-tools (ex. Peoply, Trix, IFI Rom etc.)
- A growing student library with study-resources made by IFI-students with main focus on IFI-subjects (based on IFI curriculum) and reuse
- A collection of study tools to build and represent study-resources (ex. flashcards, multiple choice, mock exam etc.)
- A low-threshold way for students — including those with little to no development experience — to contribute to and help shape the platform, building an open community around it

Note: the site is bilingual (Norwegian Bokmål + English) via wagtail-localize — new content pages generally need both locales.

## Tools and Languages
1. Framework: Django + Wagtail (CMS layer — pages, articles, categories, admin editing)
2. Languages: Python, HTML and CSS (and JavaScript. I know, I'm sorry;_;)
3. Key dependencies: wagtail-localize (nb/en translation)
4. Requirements:
    - Python
      - Minimum 3.12
      - Supported and tested on 3.12, 3.13, 3.14
    - SQLite (default, via Django)

## Setup
> **A note on file paths below:** "repo root" means the top-level folder you get from cloning (likely named `IfiPlatform`). 

>Steps also reference the `ifiplatform/` subdirectory inside it (likely named `ifiplatform`, lowercase (*not to be confused with `ifiplatform/ifiplatform_project/`, which is just the Django settings package*) — that's where manage.py, `.env` and all the Django apps actually live. Steps say which one they're relative to.

### 1. Set up Virtual Environment
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
### 2. Install dependencies
Run from the repo root:
```bash
pip install -r requirements.txt
```

### 3. Move into the ifiplatform/ folder
manage.py, `.env` and all the Django apps live in `ifiplatform/`. Every command from here on assumes you're inside it:
```bash
cd ifiplatform
```

### 4. Create .env for Secrets
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Generate local Secret key and copy generated key and replace 'your-secret-key-here' inside .env with said key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
*Editing remaining if necessary. For just development, add SecretKey and leave Debug=True. Ignore the rest*

### 5. Run Migrations
```bash
python manage.py migrate
```

### 6. Fill database with dummy data(recommended)
```bash
python manage.py seed_dev_data
```
Fills your local database with a dummy article tree (index pages, categories, a test article, a test student union and a test tool) so you're not starting from a blank site. Safe to re-run — it skips anything that already exists instead of duplicating it.

### 7. Run website on localhost
```bash
python manage.py runserver
```
Once running, open your browser and go to:
```
http://localhost:8000
```

#### Access from your phone (same Wi-Fi)
Useful for testing responsive/mobile layout on a real device.

1. Start the server bound to all network interfaces, not just localhost:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
2. Find your computer's local IP address:
   - **Windows:** run `ipconfig` in a terminal, look for `IPv4 Address` under your active adapter (e.g. `192.168.1.23`)
   - **macOS:** `ipconfig getifaddr en0` (or check System Settings → Wi-Fi → Details)
   - **Linux:** `hostname -I` or `ip addr`
3. Add that IP to `DJANGO_ALLOWED_HOSTS` in your `.env` (comma-separated, no spaces), then restart the server:
   ```
   DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,192.168.1.23
   ```
   Without this, Django rejects the request with a 400 `DisallowedHost` error — `ALLOWED_HOSTS` is read straight from this env var (`settings.py`), it isn't relaxed just because `DEBUG=True`.
4. On your phone, connected to the **same Wi-Fi network**, open:
   ```
   http://192.168.1.23:8000
   ```
   (use your own IP from step 2, not this example one)

If it still doesn't load, your computer's firewall may be blocking incoming connections on port 8000 — Windows will usually prompt to allow this the first time; allow it for at least "Private networks."

### Often used commands and actions
For a full list and explanation of this project's custom `manage.py` commands (beyond the built-in Django ones below), see [docs/operations/management_commands.md](docs/operations/management_commands.md).

#### If you change a model (i.e. need a new migration)
```bash
python manage.py makemigrations
python manage.py migrate
```
#### To create superuser/admin user
`seed_dev_data` (step 6) already creates an `admin` / `admin` superuser for
local development, so you usually don't need this. To make your own:
```bash
python manage.py createsuperuser
```
Fill out the terminal's questions
#### Running tests
```bash
python manage.py test core_app ifi_home_app account_app study_app yourpage_app
```
Explicit app labels, not a bare `manage.py test` — this project's own apps live grouped under `apps/` (see Project Structure below), and Django's default filesystem-based test discovery silently skips anything nested under a directory without an `__init__.py`, so a bare `manage.py test` would only run `core_app`'s tests. If you add a new app, add its label here too.

CI runs this same command on every PR (`.github/workflows/ci.yml`) across Python 3.12–3.14, so it's worth running locally before opening a PR.

To skip the slow whole-site crawler test (`core_app.tests.SiteCrawlTests`, tagged `slow` — it seeds a full page tree and makes real HTTP requests to every page on the site) for a quicker loop while iterating:
```bash
python manage.py test core_app ifi_home_app account_app study_app yourpage_app --exclude-tag=slow
```
#### If you change translatable text (`{% trans %}` / `_(...)`)
Update the `.po` files with the new/changed strings:
```bash
python manage.py makemessages -l nb -l en
```
Then compile them so Django actually picks up the changes:
```bash
python manage.py compilemessages
```
If that fails because `msgfmt` (part of GNU gettext) isn't installed — common on Windows, and it needs admin rights to install via `choco install gettext` — use this project's pure-Python fallback instead:
```bash
python manage.py compile_translations
```
See [docs/operations/management_commands.md](docs/operations/management_commands.md#compile_translations) for why this exists.
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
    ├── core_app/             # cross-app infrastructure: deploy notice, sitemap,
    ├── apps/                 # this project's own content/feature apps
    │   ├── ifi_home_app/     # articles, categories, homepage
    │   ├── study_app/
    │   ├── account_app/
    │   └── yourpage_app/
    ├── locale/               # i18n .po/.mo files
    └── static/ & templates/
```

## Architecture
- All project docs, sorted by topic: see [docs/README.md](docs/README.md)
- New to the code? Start with the overview: [docs/architecture/overview.md](docs/architecture/overview.md)
- Tech stack: see [docs/architecture/tech_stack.md](docs/architecture/tech_stack.md)
- Production server and deploys: see [docs/operations/prod_server.md](docs/operations/prod_server.md)
- Feature concept map: see [docs/architecture/eraser_links.md](docs/architecture/eraser_links.md)
- UI/design references: see [docs/design/figma_links.md](docs/design/figma_links.md)
- Frontend architecture (how HTML templates and CSS are organized, loaded and written): see [docs/architecture/frontend.md](docs/architecture/frontend.md)
- Picking up an AI-drafted doc to finish by hand? See [docs/claude_references/readme.md](docs/claude_references/readme.md) — those are starting points, not final docs.

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
