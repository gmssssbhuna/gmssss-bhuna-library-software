# Online Deployment Guide — Government School Bhuna Library

## Recommended first deployment: Render

This project is already prepared for a Render Web Service.

### Important database note
The application currently uses SQLite. For an online deployment, the SQLite database must be stored on persistent storage; otherwise data can disappear when a service is redeployed. The included `render.yaml` attaches a persistent disk.

### 1. Put the project on GitHub
Create a new GitHub repository, for example:
`government-school-bhuna-library`

Upload all files from this project folder.

Do NOT upload an existing `library.db` if it contains test data.

### 2. Create the Render service
In Render:
- New → Blueprint
- Select the GitHub repository
- Use the included `render.yaml`
- Deploy

The service will use:
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app`
- Health check: `/health`

### 3. Open the live website
Render will provide an HTTPS address such as:
`https://government-school-bhuna-library.onrender.com`

Student page:
`https://YOUR-DOMAIN/`

Admin:
`https://YOUR-DOMAIN/admin/login`

### 4. First login
Username: `admin`
Password: `admin123`

Immediately change this password before sharing the site publicly. The current starter version does not yet include an admin password-change screen.

### 5. Custom domain
After the service is live, a custom domain can be connected in Render, for example:
`library.yourschooldomain.in`

### 6. Production recommendation
For a real school deployment, the next hardening step should be:
- PostgreSQL instead of SQLite
- Admin password-change/reset
- Role-based admin accounts
- Automated database backups
- Audit log
- CSRF protection
- Rate limiting
- HTTPS/custom domain
- Bulk Excel/CSV import for existing library books
- Excel/PDF reports

The current package is suitable as a working MVP and can be deployed online, but those hardening items are recommended before using it as a long-term production system.
