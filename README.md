# IfiPlatform
Student platform for Ifi Uio

## Tools and Languages

1. Framework: Django
2. Languages: Python, HTML and CSS

## Setup
### Windows (PowerShell)

1. Create and activate a virtual environment:
    - python -m venv venv
    - venv\Scripts\Activate.ps1

    or with Visual Studio Code run this command: 
    - Python: Create Environment

2. Install dependencies:
    - pip install -r requirements.txt
    
    (for now there is only django to be installed, so you can also just do: pip install django)

## Documentation
### Frontend
For global static structure and conventions check out:
- [FRONTEND.md](ifiplatform\static\FRONTEND.md)

For per-app static structure:
1. Find static folder inside app
2. For CSS check out css/STYLES.md

### Backend
Sorted into packages mostly.

### Tests

## Github Actions
- linter. Recommended to use black libary (part of requierments.txt)
- Django + written tests