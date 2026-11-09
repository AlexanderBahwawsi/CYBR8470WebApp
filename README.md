# VulnLedger

**Track every security finding from discovery to fix.**

## Executive summary

A security assessment is only as useful as what happens after the report is
delivered. Findings usually end up in a PDF or a spreadsheet that goes stale
the day it is sent: nobody is sure who owns each fix, which items are overdue,
or whether "remediated" was ever verified. Small organizations such as local
governments feel this most, because they have real risk and no budget for an
enterprise vulnerability-management platform.

VulnLedger is a lightweight web application that turns an assessment report
into a living record. Security analysts log each finding with a severity, the
affected asset, and a mapping to the framework it violates (CIS Benchmarks,
NIST CSF, MITRE ATT&CK, or the OWASP Top Ten). Each finding is assigned to a
remediation owner with a due date. Owners update status as they work, managers
see open risk by severity and what is overdue on a single dashboard, and every
change is written to an append-only history so there is always an answer to
"who changed this, and when?"

What VulnLedger provides:

- **One source of truth** for findings across assessments ("engagements")
- **Framework mapping** so findings can be reported against CIS, NIST CSF, ATT&CK and OWASP
- **Clear ownership** with due dates and overdue highlighting
- **Role-based access**: analysts write, owners update their own findings, managers review
- **Audit trail** of every creation, edit, status change and export
- **CSV export** for reporting, and a **REST API** for automation

Design documentation (user stories, mis-user stories, mockup and C4
architecture diagrams) is in [`docs/README.md`](docs/README.md).

## Installation

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine with the Compose plugin)
- [Git](https://git-scm.com/downloads)

### Steps

1. Clone the repository and enter it:

   ```bash
   git clone https://github.com/AlexanderBahwawsi/CYBR8470WebApp.git
   cd CYBR8470WebApp
   ```

2. Create your environment file from the template, then open `.env` and change
   `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD` and `DEMO_PASSWORD`:

   ```bash
   cp .env.example .env
   ```

   On Windows PowerShell use `Copy-Item .env.example .env`.

3. Build and start the containers. Database migrations run automatically:

   ```bash
   docker compose up --build
   ```

4. In a second terminal, load the role groups, demo accounts and sample data:

   ```bash
   docker compose exec web python manage.py seed_demo
   ```

5. Optional: create an administrator account for the Django admin site:

   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

To stop the application press `Ctrl+C`, or run `docker compose down`
(add `-v` to also delete the database volume).

### Running without Docker

For a quick local run, the application falls back to SQLite when
`POSTGRES_HOST` is not set:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DJANGO_DEBUG=1                                # PowerShell: $env:DJANGO_DEBUG=1
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

### Running the tests

```bash
docker compose exec web python manage.py test
```

## Getting started

1. Open <http://localhost:8000> and sign in. `seed_demo` creates one account
   per role, all using the `DEMO_PASSWORD` value from your `.env` file:

   | Username  | Role    | Can do                                                    |
   |-----------|---------|-----------------------------------------------------------|
   | `analyst` | Analyst | Create and edit engagements and findings, change any status, export |
   | `owner`   | Owner   | View everything, change the status of findings assigned to them |
   | `manager` | Manager | View everything, export CSV                               |

2. **Dashboard** – the landing page shows open findings by severity, what is
   overdue, what is assigned to you, and recent activity. Click a tile to jump
   to the matching findings.

3. **Record a finding** (as `analyst`) – choose **New finding**, pick the
   engagement, give it a title, description, severity, the framework and
   control reference (for example `CIS 1.5` or `A01:2021`), an owner and a due
   date, then **Save**.

4. **Work a finding** (as `owner`) – open a finding assigned to you, pick a new
   status, add a short note, and choose **Save status**. The change appears in
   the finding's **History**.

5. **Find and report** – on **Findings**, search or filter by severity, status
   or engagement, then choose **Export CSV** to download exactly what is on
   screen.

6. **REST API** – while signed in, browse <http://localhost:8000/api/> for
   `findings` and `engagements` endpoints (JSON; supports `?status=` and
   `?severity=` on findings).

7. **Administration** – user accounts and role membership are managed at
   <http://localhost:8000/admin/> with a superuser account.

> The demo accounts exist for evaluation only. Remove them, set
> `DJANGO_DEBUG=0`, and serve the application behind HTTPS before storing real
> findings.

## License

VulnLedger is released under the [MIT License](LICENSE).
