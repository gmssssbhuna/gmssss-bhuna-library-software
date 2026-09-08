# Government School Bhuna — Online Library Management System

A complete Flask + SQLite web application based on the supplied library-system requirements.

## Features
- Public student book search without login
- Search by book name, author, subject, class, accession number
- Availability: Available / Currently Issued
- Secure admin login
- Add, edit, deactivate/reactivate books
- Student records
- Issue and return records
- Automatic availability update
- Dashboard with basic statistics
- Responsive interface

## Default admin
Username: `admin`
Password: `admin123`

**Change the password before deploying publicly.**

## Run locally

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run:

```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
```

macOS/Linux:
```bash
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Start:
```bash
python app.py
```

6. Open:
`http://127.0.0.1:5000`

Admin:
`http://127.0.0.1:5000/admin/login`

The SQLite database `library.db` is created automatically on first run.

## Production notes
Use a strong `SECRET_KEY`, change the admin password, disable Flask debug mode, and deploy behind a production WSGI server such as Gunicorn/waitress with HTTPS.
