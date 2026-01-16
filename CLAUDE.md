# CLAUDE.md - ASNC Platform

## Project Overview

This is the **ASNC Platform** (Asociación Nuclear Colombiana) - a Django 6.0 web application for managing membership admissions and providing an administrative portal for committee members.

**Official Domain:** www.asncol.com
**Contact Email:** info@asncol.com

## Tech Stack

- **Framework**: Django 6.0
- **Database**: PostgreSQL
- **Frontend**: Bootstrap 5.3.0, Bootstrap Icons, Google Fonts (Outfit), anime.js (scroll animations)
- **Forms**: Django Crispy Forms with Bootstrap 5 template pack
- **Auth**: Custom User model with email-based authentication
- **Storage**: django-storages + boto3 (AWS S3 for production)
- **Config**: python-decouple for environment variables
- **Localization**: Spanish Colombia (es-co), Timezone America/Bogota

## Project Structure

```
asnc_platform/
├── config/                      # Django project settings, URLs, WSGI/ASGI
├── users/                       # Custom User model (email as USERNAME_FIELD)
├── admissions/                  # Membership application workflow
│   └── templates/admissions/    # Form, success page
│       └── emails/              # HTML email templates
├── dashboard/                   # Admin portal for committee members
│   └── templates/dashboard/     # Dashboard templates (including base_dashboard.html)
├── website/                     # Public-facing homepage
│   └── templates/website/       # Homepage with animations
├── templates/                   # Base templates (base.html)
├── static/images/               # Static assets (logos, hero images)
├── media/                       # User uploads (CVs in applications/cvs/)
├── requirements.txt             # Python dependencies
└── .env                         # Environment variables (not in git)
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
- `cv_file`: FileField for CV uploads (to `applications/cvs/`)
- `status`: PENDING | REVIEW | APPROVED | REJECTED | COMPLETED
- `admin_notes`: Internal committee notes
- `created_at`, `updated_at`: Timestamps
- Ordering: `-created_at` (newest first)

**Status Choices (Spanish labels):**
| Code | Label |
|------|-------|
| PENDING | Pendiente de Revisión |
| REVIEW | En Estudio |
| APPROVED | Aprobado |
| REJECTED | Rechazado |
| COMPLETED | Vinculado (Usuario Creado) |

## URL Structure

```
/                              → Public homepage
/solicitud/                    → Membership application form
/gracias/                      → Application success page
/portal/login/                 → Dashboard login
/portal/logout/                → Dashboard logout
/portal/                       → Dashboard home (protected)
/portal/solicitudes/           → Application list (protected)
/portal/solicitudes/<id>/      → Application detail (protected)
/portal/solicitudes/<id>/cambiar-estado/<status>/  → Change application status
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
# Core Django
DEBUG=True
SECRET_KEY=<your-secret-key>
ALLOWED_HOSTS=127.0.0.1,localhost

# PostgreSQL Database
DB_NAME=asnc_db
DB_USER=postgres
DB_PASSWORD=<password>
DB_HOST=localhost
DB_PORT=5432

# AWS S3 (Production only, when DEBUG=False)
S3_CLIENT_PREFIX=asnc          # Prefix for S3 paths (e.g., asnc/static/, asnc/media/)
# Note: AWS credentials configured via AWS_STORAGE_BUCKET_NAME='vadomdata' in settings
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
- Dashboard base: `dashboard/templates/dashboard/base_dashboard.html`
- Email templates: `admissions/templates/admissions/emails/`
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

### Frontend Assets (CDN)
- Bootstrap 5.3.0 (CSS + JS)
- Bootstrap Icons
- Google Fonts: Outfit
- anime.js - Used for scroll animations on homepage (SVG fission effect, data visualization)

## Application Workflow

1. **Public User**: Visits homepage → Fills application form → Receives confirmation email
2. **Committee**: Logs into portal → Views dashboard KPIs → Reviews applications → Approves/Rejects
3. **System**: Sends email notifications on status changes

## Views Summary

### Website App
- `HomeView` (TemplateView) - Public homepage with hero sections and animations

### Admissions App
- `ApplicationCreateView` (CreateView) - Membership application form
- `ApplicationSuccessView` (TemplateView) - Confirmation page
- `ApplicationListView` (LoginRequiredMixin, ListView) - Dashboard application list
- `ApplicationDetailView` (LoginRequiredMixin, DetailView) - Application details
- `change_application_status()` - Function-based view for status changes
- `send_application_email()` - Helper function for HTML email notifications

### Dashboard App
- `CustomLoginView` (LoginView) - Email-based login
- `DashboardHomeView` (LoginRequiredMixin, TemplateView) - KPIs dashboard

## Authentication Flow

- Login URL: `/portal/login/`
- Logout URL: `/portal/logout/`
- Uses email (not username) for authentication
- Protected views redirect to login if not authenticated
- After login, redirects to `/portal/` (dashboard home)
- After logout, redirects to `/portal/login/`
- Settings: `LOGIN_URL = 'login'`, `LOGIN_REDIRECT_URL = 'dashboard_home'`, `LOGOUT_REDIRECT_URL = 'login'`

## Key Files to Know

- `config/settings.py` - All Django settings (includes S3 storage config)
- `config/urls.py` - Root URL configuration
- `admissions/models.py` - MembershipApplication model
- `admissions/views.py` - Application form, success views, email sending
- `admissions/forms.py` - MembershipApplicationForm
- `admissions/admin.py` - Admin with custom actions (approve/reject)
- `dashboard/views.py` - Dashboard, list, detail, status change views
- `dashboard/urls.py` - Protected portal URL patterns
- `users/models.py` - Custom User model
- `templates/base.html` - Main layout with navbar/footer
- `dashboard/templates/dashboard/base_dashboard.html` - Dashboard sidebar layout

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

## Storage Configuration

### Development (DEBUG=True)
- Static files: `/static/` served locally
- Media files: `/media/` served locally via FileSystemStorage

### Production (DEBUG=False)
- Uses AWS S3 via django-storages and boto3
- Bucket: `vadomdata`
- Region: `us-east-1`
- Static location: `{S3_CLIENT_PREFIX}/static/`
- Media location: `{S3_CLIENT_PREFIX}/media/`
- Custom storage classes: `StaticStorage`, `MediaStorage` in settings.py

## Dashboard Sidebar Structure

The dashboard uses a fixed sidebar (280px) with the following menu structure:

```
PRINCIPAL
├── Inicio (dashboard_home)
└── Solicitudes (application_list)

GESTIÓN ACADÉMICA
├── Eventos (placeholder)
├── Publicaciones (placeholder)
└── Congresos (placeholder)

ADMINISTRACIÓN
├── Reportes (placeholder)
├── Usuarios (placeholder)
└── Configuración (placeholder)
```

Note: Items marked as "placeholder" are not yet implemented.

## Django Admin Configuration

### MembershipApplicationAdmin (`admissions/admin.py`)
- **List display**: full_name, email, profession, status (colored), cv_link, created_at
- **Filters**: status, created_at, profession
- **Search**: first_name, last_name, email, uuid
- **Read-only**: uuid, created_at, updated_at
- **Custom actions**:
  - `approve_application()` - Sets status to APPROVED, sends email notification
  - `reject_application()` - Sets status to REJECTED
- **Status color coding**: PENDING (orange), REVIEW (blue), APPROVED (green), REJECTED (red), COMPLETED (black)

## Email Configuration

- Development: Console backend (prints to terminal)
- Production: Configure SMTP in settings.py (TODO)
- Default from: `no-reply@asncol.com`
- Contact email: `info@asncol.com`
- Email templates: `admissions/templates/admissions/emails/application_received.html`
- Uses `EmailMultiAlternatives` for HTML + plain text

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Django | 6.0 | Web framework |
| psycopg2-binary | 2.9.11 | PostgreSQL adapter |
| django-crispy-forms | 2.5 | Form rendering |
| crispy-bootstrap5 | 2025.6 | Bootstrap 5 form pack |
| django-storages | 1.14.6 | S3 storage backend |
| boto3 | 1.42.29 | AWS SDK for S3 |
| python-decouple | 3.8 | Environment variables |

## Future Enhancements (TODO)

- [ ] REST API endpoints
- [ ] Member directory
- [ ] Payment integration
- [ ] Auto-create user account on approval (comment exists in code)
- [ ] Role-based access control
- [ ] Two-factor authentication
- [ ] Celery for async email queue
- [ ] Configure SMTP for production emails
- [ ] Pagination on application list
- [ ] Rejection email notification
- [ ] Search/filter functionality on dashboard list
