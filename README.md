# AICTE SmartFlow — Integrated Workflow Automation, Compliance Monitoring and Alert Management System

> **Project Code:** SIH26262  
> **System Notice:** AICTE SmartFlow is a workflow and compliance prototype. It is not an AICTE service and does not bundle authoritative regulatory thresholds. Compliance rules must be configured with a source and effective date verified by an authorized administrator; otherwise the relevant checks require manual review.

---

## 1. System Overview & Key Capabilities

AICTE SmartFlow replaces manual, error-prone institutional approval workflows with an intelligent, role-governed digital pipeline:

- **Role-Based Portals:** Dedicated experiences for **Institution Users**, **Scrutiny Officers**, **Regional Directors**, and **System Administrators**.
- **Controlled Workflow Engine:** Enforces strictly valid state transitions:  
  `DRAFT → SUBMITTED → IN_SCRUTINY → DEFICIENCY_FLAGGED → IN_SCRUTINY → APPROVED / REJECTED`
- **Institution Master Records:** Campus profile, contiguous land area, instructional built-up area, academic programmes/courses, and faculty register.
- **Secure Document Management:** Supports workflow document categories, file-type and size validation, versioned replacements, and permission-checked downloads.
- **Modular AI Document Pre-Checking:** PyMuPDF-based text and metadata extraction, keyword verification, certificate validity checks, and an explicit disclaimer for human officer confirmation.
- **Configurable Compliance Engine:** Evaluates configured, active, source-verified rules and application data. Missing or unverified regulatory rules are sent for manual review rather than treated as authoritative.
- **Deadline Monitoring & Alert Management:** Management command with 24-hour alert deduplication for overdue scrutiny (>7 days) and expiring certificates.
- **Audit Trail & Security:** Immutable logging of logins, transitions, and uploads with automatic sensitive data sanitization (no passwords/tokens recorded).
- **Rule-Based FAQ Chatbot:** Instant guidance on submission steps, document requirements, status meanings, and deficiency resolution.

---

## 2. Technology Stack

- **Backend:** Python 3.11+, Django 6.1.2
- **Document Processing:** PyMuPDF (`pymupdf`)
- **Database:** SQLite (default local development); PostgreSQL-ready
- **Frontend & UI:** Django Templates, HTML5, Vanilla CSS, Bootstrap 5.3, Bootstrap Icons, Chart.js
- **Email Backend:** Console email backend (development); SMTP/SES configurable for production

---

## 3. Team Member Quick-Start Guide (Windows & Linux)

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-org/AICTE_SmartFlow.git
cd AICTE_SmartFlow
```

### Step 2: Create and Activate Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run Database Migrations
```bash
cd config
python manage.py migrate
```

### Step 5: Seed Demo Users and Sample Data
Run the built-in demo seeder to create demo accounts, institution profiles, and sample applications. It does not seed regulatory thresholds:
```bash
python manage.py seed_demo_data
```

### Step 6: Start the Development Server
```bash
python manage.py runserver
```
Visit **http://127.0.0.1:8000/** in your web browser.

---

## 4. Default Demo Accounts

All demo accounts are created with password: `Test@1234`

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Institution User** | `inst_user` | `Test@1234` | Create drafts, upload documents, submit applications, respond to deficiencies. |
| **Scrutiny Officer** | `scrutiny_officer` | `Test@1234` | Review assigned applications, verify documents, view AI findings, flag deficiencies, recommend approval/rejection. |
| **Regional Director** | `regional_director` | `Test@1234` | Executive workload metrics, stage charts, overdue SLA monitoring, handbook rule configuration. |
| **System Administrator**| `admin_user` | `Test@1234` | Full system governance, audit trail access, user roles, rule adjustments. |
| **Existing Superuser** | `gajalakshmi` | *(existing)* | Django admin superuser access. |

---

## 5. Automated Test Suite Execution

Run the automated unit and integration tests:
```bash
python manage.py test
```
**Test coverage includes** account registration and logout, role and institution data isolation, application draft/workflow behavior, protected document upload and review, compliance rule verification, notification actions, deadline alerts, and audit-log sanitization.

---

## 6. Deadline Management & Alert Scheduling

To scan for overdue applications (>7 days) and expiring documents:
```bash
python manage.py check_deadlines
```

### Scheduling on Windows (Task Scheduler)
1. Open **Task Scheduler** on Windows.
2. Select **Create Basic Task** &bull; Name: `AICTE_Check_Deadlines`.
3. Trigger: **Daily** at `08:00 AM`.
4. Action: **Start a program**:
   - **Program/script:** `F:\AICTE\AICTE_SmartFlow\venv\Scripts\python.exe`
   - **Arguments:** `manage.py check_deadlines`
   - **Start in:** `F:\AICTE\AICTE_SmartFlow\config`

### Scheduling on Linux (Cron)
Add the following line via `crontab -e`:
```cron
0 8 * * * /path/to/venv/bin/python /path/to/config/manage.py check_deadlines >> /var/log/aicte_deadlines.log 2>&1
```

---

## 7. Interactive Walkthrough Demo Guide

### Flow 1: Institution User
1. Log in as `inst_user` / `Test@1234`.
2. View **Campus & Infrastructure** under Institution Master to see land (3.5 acres) and library volumes.
3. Click **+ New Application** to create a draft application for the desired academic year.
4. Open the application, upload supporting documents (e.g., Land Title PDF, Fire Safety NOC).
5. Click **Submit Application**. The status transitions to `SUBMITTED`; configured verified checks run, and other regulatory checks remain flagged for manual review.

### Flow 2: Scrutiny Officer
1. Log in as `scrutiny_officer` / `Test@1234`.
2. You will be redirected to the **Scrutiny Desk** (`/officer/dashboard/`).
3. Click **Review** on an application in the pipeline.
4. Verify uploaded documents, review the **AI Pre-Check findings**, inspect the **Compliance Report**, and choose an action:
   - To request updates, select **Flag Deficiencies**, provide detailed notes, and submit.
   - To approve, select **Approve in SmartFlow** and submit. This records a workflow decision, not an AICTE statutory approval.

### Flow 3: Regional Director & Executive Analytics
1. Log in as `regional_director` / `Test@1234`.
2. You will land on the **Executive Analytics Portal** (`/admin-portal/dashboard/`).
3. Review total application counts, stage distribution doughnut chart, officer workload distribution, and overdue SLA counters.
4. Access **Handbook Rules** to view or adjust regulatory parameters.
5. Access **Audit Trail** to inspect tamper-evident security logs.
