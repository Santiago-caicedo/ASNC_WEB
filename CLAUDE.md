# CLAUDE.md - ASNC Platform

## Project Overview

This is the **ASNC Platform** (Asociación Nuclear Colombiana) - a Django 6.0 web application for managing membership admissions and providing an administrative portal for committee members.

## Tech Stack

- **Framework**: Django 6.0
- **Database**: PostgreSQL
- **Frontend**: Bootstrap 5.3.0, Bootstrap Icons, Google Fonts (Outfit)
- **Forms**: Django Crispy Forms with Bootstrap 5 template pack
- **Auth**: Custom User model with email-based authentication
- **Config**: python-decouple for environment variables

## Project Structure

```
asnc_platform/
├── config/              # Django project settings, URLs, WSGI/ASGI
├── users/               # Custom User model (email as USERNAME_FIELD)
├── admissions/          # Membership application workflow
├── dashboard/           # Admin portal for committee members
├── website/             # Public-facing homepage
├── templates/           # Base templates (base.html)
├── static/images/       # Static assets (logos, hero images)
├── media/               # User uploads (CVs stored in applications/cvs/)
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables (not in git)
```

## Django Apps

| App | Purpose |
|-----|---------|
| `users` | Custom User model extending AbstractUser, email-based auth |
| `admissions` | MembershipApplication model, form submission, email notifications |
| `dashboard` | Protected admin views, KPIs, application management |
| `website` | Public homepage with marketing content |

## Key Models

### User (`users/models.py`)
- Extends `AbstractUser`
- `email` is the primary authentication field (unique)
- Standard Django auth fields

### MembershipApplication (`admissions/models.py`)
- `uuid`: Unique identifier for tracking
- `first_name`, `last_name`, `email`, `phone`
- `profession`, `current_job`, `institution`, `linkedin_url`
- `cv_file`: FileField for CV uploads
- `status`: PENDING | REVIEW | APPROVED | REJECTED | COMPLETED
- `admin_notes`: Internal committee notes
- `created_at`, `updated_at`: Timestamps

## URL Structure

```
/                              → Public homepage
/solicitud/                    → Membership application form
/gracias/                      → Application success page
/portal/login/                 → Dashboard login
/portal/                       → Dashboard home (protected)
/portal/solicitudes/           → Application list (protected)
/portal/solicitudes/<id>/      → Application detail (protected)
/admin/                        → Django admin
```

## Development Commands

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Run development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files (production)
python manage.py collectstatic

# Django shell
python manage.py shell
```

## Environment Variables (.env)

```
DEBUG=True
SECRET_KEY=<your-secret-key>
ALLOWED_HOSTS=127.0.0.1,localhost
DB_NAME=asnc_db
DB_USER=postgres
DB_PASSWORD=<password>
DB_HOST=localhost
DB_PORT=5432
```

## Code Conventions

### Python/Django
- Use Spanish for user-facing content (labels, messages, templates)
- Use English for code (variable names, comments, docstrings)
- Follow Django conventions for model/view naming
- Use Class-Based Views for complex logic
- Use `LoginRequiredMixin` for protected views
- Forms use `crispy_forms` with Bootstrap 5

### Templates
- Base template: `templates/base.html`
- Dashboard base: `templates/dashboard/base_dashboard.html`
- Use `{% load crispy_forms_tags %}` for forms
- CSS variables defined in base.html:
  - `--asnc-navy: #1B2A41`
  - `--asnc-blue: #213a5c`
  - `--asnc-gold: #f4c343`
  - `--asnc-bg: #F5F7FA`

### Static Files
- Images: `static/images/`
- Use `{% static 'path' %}` template tag
- Media uploads go to `media/` directory

## Application Workflow

1. **Public User**: Visits homepage → Fills application form → Receives confirmation email
2. **Committee**: Logs into portal → Views dashboard KPIs → Reviews applications → Approves/Rejects
3. **System**: Sends email notifications on status changes

## Authentication Flow

- Login URL: `/portal/login/`
- Uses email (not username) for authentication
- Protected views redirect to login if not authenticated
- After login, redirects to `/portal/` (dashboard home)

## Key Files to Know

- `config/settings.py` - All Django settings
- `config/urls.py` - Root URL configuration
- `admissions/models.py` - MembershipApplication model
- `admissions/views.py` - Application form and success views
- `admissions/forms.py` - MembershipApplicationForm
- `dashboard/views.py` - Dashboard, list, detail, status change views
- `users/models.py` - Custom User model
- `templates/base.html` - Main layout with navbar/footer

## Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test admissions
python manage.py test users
```

## Common Tasks

### Add a new field to MembershipApplication
1. Edit `admissions/models.py`
2. Run `python manage.py makemigrations`
3. Run `python manage.py migrate`
4. Update `admissions/forms.py` if needed
5. Update templates to display new field

### Add a new dashboard view
1. Create view in `dashboard/views.py` with `LoginRequiredMixin`
2. Add URL pattern in `dashboard/urls.py`
3. Create template in `templates/dashboard/`
4. Add navigation link in `base_dashboard.html`

### Modify application status workflow
1. Update `STATUS_CHOICES` in `admissions/models.py`
2. Update `change_application_status` view in `admissions/views.py`
3. Update status badge styling in templates

## Security Notes

- CSRF protection enabled on all forms
- Sensitive data in `.env` file (not committed)
- Media files stored outside web root
- Email-based auth (harder to guess than usernames)
- Protected views use Django's authentication mixins

## Database

- PostgreSQL (configured via .env)
- Migrations stored in each app's `migrations/` folder
- Custom User model: `AUTH_USER_MODEL = 'users.User'`

## Email Configuration

- Development: Console backend (prints to terminal)
- Production: Configure SMTP in settings.py
- Default from: `no-reply@asocnuclear.org`

## Future Enhancements (TODO)

- [ ] REST API endpoints
- [ ] Member directory
- [ ] Payment integration
- [ ] Auto-create user account on approval
- [ ] Role-based access control
- [ ] Two-factor authentication
- [ ] Celery for async email queue
