# IfiPlatform
Student platform for IFI-UIO by students for students

## About
Goals:
- One place find information for IFI-students
- One place to find IFI-tools (ex. Peoply, Trix, IFI Rom etc.)
- A growing student library with study-resources made by IFI-students with main focus on IFI-subjects (based on IFI curriculum) and reuse
- A collection of study tools to build and represent study-resources (ex. flashcards, multiple choice, mock exam etc.)

## Tools and Languages
1. Framework: Django
2. Languages: Python, HTML and CSS
3. Requirements: Python 3.x (specify version here), SQLite (default, via Django)

## Setup
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
#### Or through Visual Studio COde
Run this command from the Command Palette:
```bash
Python: Create Environment
```
### Install dependencies
```bash
pip install -r <path to requirements.txt>
```
### Run website on localhost
```bash
py <path to manage.py> runserver
```
Once running, open your browser and go to:
```
http://localhost:8000
```

## Project Structure (coming)
```
IfiPlatform/
├── manage.py
├── requirements.txt
├── <app_name>/
│   ├── models.py
│   ├── views.py
│   └── templates/
└── README.md
```

## Architecture (coming)
Check out...

## Tutorials (coming)
Check out [TUTORIALS.md](TUTORIALS.md) for more about Django Framework and other dependencies used in this project.

## Contributing
We welcome contributions from IFI students! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to open issues (bug/feature/task reports, with examples)
- How to submit pull requests
- Code style expectations (Black/Pylint)
- The different contributor roles in this project

## License (coming)
This project is licensed under the...
