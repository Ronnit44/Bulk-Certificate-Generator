```markdown
# Bulk Certificate Generator API

A Django + Django REST Framework API for generating personalized certificates in bulk.

The API accepts a single request containing multiple recipients, generates one PDF per
recipient using a predefined template, tracks each recipient independently, and provides
endpoints to check job status and download certificates.

## Tech Stack

- Python
- Django
- Django REST Framework
- SQLite
- ReportLab

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
```

## Run

```powershell
python manage.py runserver
```

The API is available at:

```text
http://127.0.0.1:8000/
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/jobs/` | Create a bulk certificate-generation job |
| GET | `/api/jobs/<job_id>/` | Check job status and recipient results |
| GET | `/api/jobs/<job_id>/certificates/<recipient_id>/download/` | Download a certificate |

## Create a Generation Job

A single request can contain multiple recipients.

```http
POST /api/jobs/
Content-Type: application/json
```

Example:

```json
{
    "course_name": "Django Fundamentals",
    "completion_date": "2026-10-08",
    "issuer_name": "Acme Academy",
    "recipients": [
        {
            "name": "Ada Lovelace",
            "email": "ada@example.com"
        },
        {
            "name": "Grace Hopper",
            "email": "grace@example.com"
        }
    ]
}
```

The request validates the job information and each recipient. A maximum of 1000
recipients is accepted per job.

The API processes all recipients as one generation job and returns the result for
each recipient.

## Check Job Status

```http
GET /api/jobs/<job_id>/
```

The response contains:

- Job status
- Total recipients
- Successful generations
- Failed generations
- Progress percentage
- Individual recipient results
- Certificate download URLs

Example:

```json
{
    "status": "completed",
    "total_count": 2,
    "success_count": 2,
    "failure_count": 0,
    "progress_percent": 100.0
}
```

Possible job statuses include:

- `completed`
- `completed_with_errors`

If one certificate fails, that recipient is marked as failed while other recipients
continue to be processed.

## Retrieve a Certificate

```http
GET /api/jobs/<job_id>/certificates/<recipient_id>/download/
```

This returns the generated certificate as a PDF.

## Certificate Generation

The application uses a single predefined certificate template created with ReportLab.

Each certificate contains recipient-specific information such as:

- Recipient name
- Course name
- Completion date
- Issuer name

No template editor or multiple certificate designs are required.

## Bulk Processing Design

The API is designed around bulk generation:

```text
One API request
      |
      +-- Recipient 1 → Certificate
      +-- Recipient 2 → Certificate
      +-- Recipient 3 → Certificate
      +-- Recipient N → Certificate
```

The application currently uses **synchronous processing**.

The flow is:

1. Create the generation job.
2. Create recipient records.
3. Generate each certificate.
4. Record successful and failed generations.
5. Update job status and counts.
6. Return the completed job.

Synchronous processing was chosen because it keeps the application simple and requires
no additional task queue or worker infrastructure. The certificate-generation logic is
kept in a separate service layer, so background processing such as Celery or RQ could
be introduced later without changing the API contract.

## Failure Handling

A failure for one recipient does not stop the remaining recipients.

For example:

```text
Recipient 1 → Generated
Recipient 2 → Failed
Recipient 3 → Generated
```

The job would report:

```text
total_count   = 3
success_count = 2
failure_count = 1
```

and use the `completed_with_errors` status.

Invalid input returns `400 Bad Request`.

## Project Structure

```text
certificate-generator/
│
├── certificate_generator/
│   ├── settings.py
│   ├── urls.py
│   └── ...
│
├── certificates/
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── services.py
│   ├── urls.py
│   ├── views.py
│   └── tests.py
│
├── media/
├── manage.py
├── requirements.txt
└── README.md
```

## Tests

Run:

```powershell
python manage.py test
```

The tests cover:

- Creating a generation job
- Input validation
- Certificate generation
- Job status and progress
- Individual certificate-generation failure
- Certificate retrieval

## Design Decisions

### Synchronous Processing

Synchronous processing was chosen to keep the implementation straightforward while
supporting bulk generation. The assignment permits synchronous or background processing.

### Relational Persistence

`GenerationJob` stores the overall generation request and aggregate progress.

`RecipientCertificate` stores the result of each individual certificate generation,
including its status, generated file, and any error message.

### PDF Generation

ReportLab is used to generate certificates from a single predefined template.

### File Storage

Generated certificates use Django's file storage abstraction, allowing the storage
mechanism to be changed later if required.
