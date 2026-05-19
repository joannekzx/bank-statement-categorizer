# Bank Statement Categorizer

Parses Singapore bank PDF statements and returns categorized spending data

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run
```bash
uvicorn backend.main:app --reload
```