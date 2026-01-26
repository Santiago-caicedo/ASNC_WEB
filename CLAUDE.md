# CLAUDE.md - ASNC Platform

## Project Overview

This is the **ASNC Platform** (Asociación Nuclear Colombiana) - a Django 6.0 web application for managing membership admissions, email communications, and providing an administrative portal for committee members.

**Official Domain:** www.asncol.com
**Contact Email:** info@asncol.com
**Location:** Bucaramanga, Santander, Colombia

## Tech Stack

- **Framework**: Django 6.0
- **Database**: PostgreSQL
- **Frontend**: Bootstrap 5.3.0, Bootstrap Icons, Google Fonts (Outfit), anime.js (scroll animations)
- **Forms**: Django Crispy Forms with Bootstrap 5 template pack
- **Auth**: Custom User model with email-based authentication
- **Storage**: django-storages + boto3 (AWS S3 for production)
- **Config**: python-decouple for environment variables
- **Images**: Pillow (for ImageField support)
- **SEO**: django.contrib.sitemaps
- **Email**: SMTP with SSL (BanaHosting/MailChannels)
- **Localization**: Spanish Colombia (es-co), Timezone America/Bogota

## Project Structure

```
asnc_platform/
├── config/                      # Django project settings, URLs, WSGI/ASGI
├── users/                       # Custom User model (email as USERNAME_FIELD)
├── admissions/                  # Membership application workflow
│   └── templates/admissions/    # Form, success page
│       └── emails/              # HTML email templates (application_received.html)
├── dashboard/                   # Admin portal for committee members
│   ├── models.py                # SentEmail model (email history)
│   ├── forms.py                 # FeaturedMemberForm, EmailComposeForm
│   └── templates/dashboard/     # Dashboard templates
│       ├── featured_members/    # CRUD templates for featured members
│       └── emails/              # Email compose, history, detail templates
├── website/                     # Public-facing pages
│   ├── templates/website/       # Home, About, Events, PowerPoint template
│   ├── models.py                # FeaturedMember model
│   ├── views.py                 # HomeView, AboutView, EventsView, PowerPointTemplateView
│   └── sitemaps.py              # SEO sitemaps
├── templates/                   # Base templates
│   ├── base.html                # Main layout with SEO meta tags
│   ├── robots.txt               # SEO robots file
│   ├── emails/                  # Reusable email templates
│   │   └── base_email.html      # ASNC branded email template
│   ├── 400.html                 # Bad request error page
│   ├── 403.html                 # Forbidden error page
│   ├── 403_csrf.html            # CSRF error page
│   ├── 404.html                 # Not found error page
│   └── 500.html                 # Server error page
├── static/images/               # Static assets (logos, hero images, favicon)
├── media/                       # User uploads (CVs, member photos)
├── requirements.txt             # Python dependencies
└── .env                         # Environment variables (not in git)
```

## Django Apps

| App | Purpose |
|-----|---------|
| `users` | Custom User model extending AbstractUser, email-based auth |
| `admissions` | MembershipApplication model, form submission, email notifications |
| `dashboard` | Protected admin views, KPIs, application management, featured members CRUD, email mailing system |
| `website` | Public pages: homepage, about, events, PowerPoint template |

## Key Models

### User (`users/models.py`)
- Extends `AbstractUser`
- `email` is the primary authentication field (unique)
- Standard Django auth fields

### MembershipApplication (`admissions/models.py`)
- `uuid`: Unique identifier for tracking
- `first_name`, `last_name`, `email`, `phone` (optional)
- `profession`, `current_job`, `institution`, `linkedin_url`
- `contribution_statement`: TextField for applicant's motivation
- `cv_file`: FileField for CV uploads (to `applications/cvs/`)
- `status`: PENDING | REVIEW | APPROVED | REJECTED | COMPLETED
- `admin_notes`: Internal committee notes
- `created_at`, `updated_at`: Timestamps
- Ordering: `-created_at` (newest first)
- **Meta:** `verbose_name = 'Solicitud de Ingreso'`

**Status Choices (Spanish labels):**
| Code | Label |
|------|-------|
| PENDING | Pendiente de Revisión |
| REVIEW | En Estudio |
| APPROVED | Aprobado |
| REJECTED | Rechazado |
| COMPLETED | Vinculado (Usuario Creado) |

### FeaturedMember (`website/models.py`)
- `full_name`: CharField (200)
- `photo`: ImageField (upload to `featured_members/`)
- `association_position`: CharField - Role in ASNC
- `profession`: CharField
- `professional_trajectory`: TextField
- `linkedin_url`: URLField (optional)
- `is_active`: BooleanField (default True)
- `display_order`: PositiveIntegerField (for sorting)
- `created_at`, `updated_at`: Timestamps
- Ordering: `['display_order', 'full_name']`
- **Meta:** `verbose_name = 'Asociado Destacado'`

### SentEmail (`dashboard/models.py`)
- `subject`: CharField (255)
- `message`: TextField
- `recipients`: TextField (comma-separated emails)
- `recipients_count`: PositiveIntegerField
- `sent_by`: ForeignKey to User (null=True, on_delete=SET_NULL)
- `sent_at`: DateTimeField (auto_now_add)
- `success`: BooleanField (default True)
- `error_message`: TextField (for failed sends)
- Ordering: `['-sent_at']`
- **Meta:** `verbose_name = 'Correo Enviado'`
- **Methods:**
  - `get_recipients_list()`: Returns list of emails parsed from comma-separated string

## URL Structure

```
# Public Website
/                              → Homepage (HomeView)
/quienes-somos/                → About page with team (AboutView)
/eventos/                      → Events page - under construction (EventsView)
/recursos/plantilla-presentacion/ → PowerPoint template page
/solicitud/                    → Membership application form
/gracias/                      → Application success page

# SEO
/sitemap.xml                   → Dynamic XML sitemap
/robots.txt                    → Robots file for crawlers

# Dashboard (Protected)
/portal/login/                 → Dashboard login
/portal/logout/                → Dashboard logout
/portal/                       → Dashboard home with KPIs
/portal/solicitudes/           → Application list
/portal/solicitudes/<id>/      → Application detail
/portal/solicitudes/<id>/cambiar-estado/<status>/  → Change status

# Featured Members CRUD (Protected)
/portal/asociados-destacados/              → List featured members
/portal/asociados-destacados/nuevo/        → Create new member
/portal/asociados-destacados/<id>/editar/  → Edit member
/portal/asociados-destacados/<id>/eliminar/ → Delete member

# Email Module (Protected)
/portal/correos/               → Email history list
/portal/correos/redactar/      → Compose new email
/portal/correos/<id>/          → Email detail view

# Admin
/admin/                        → Django admin
```

## Django Admin Configuration

### MembershipApplicationAdmin (`admissions/admin.py`)
Full-featured admin for managing applications:

**List Display:**
- `full_name()` - Concatenates first_name + last_name
- `email`, `profession`
- `status_colored()` - Color-coded status badges
- `cv_link()` - Direct link to download CV
- `created_at`

**Filters & Search:**
- `list_filter`: status, created_at, profession
- `search_fields`: first_name, last_name, email, uuid

**Readonly Fields:** uuid, created_at, updated_at

**Admin Actions:**
- `approve_application()` - Sets status to APPROVED
- `reject_application()` - Sets status to REJECTED

**Note:** Other apps (users, dashboard, website) have empty admin.py files. FeaturedMember is managed via the dashboard CRUD, not Django admin.

## Email System

### SMTP Configuration
The platform uses SMTP with SSL for sending emails:
- **Host**: bh8928.banahosting.com (BanaHosting/MailChannels)
- **Port**: 465 (SSL)
- **From**: info@asncol.com

### Email Templates
1. **Base Email** (`templates/emails/base_email.html`)
   - ASNC branded template with logo
   - Used for all outgoing emails from mailing module
   - Social media links (LinkedIn, Instagram, Facebook)

2. **Application Received** (`admissions/templates/admissions/emails/application_received.html`)
   - Sent when user submits membership application
   - Includes: greeting, next steps (1-2-3), mission quote

### Mailing Module Features
- **Compose**: Send emails to manual addresses, system users, or applicants
- **History**: View all sent emails with status
- **Detail**: View full email content and recipient list
- **BCC**: Recipients are sent via BCC for privacy

### Email Sending Functions

**`send_application_email()`** (`admissions/views.py`)
- Renders HTML template: `admissions/emails/application_received.html`
- Creates `EmailMultiAlternatives` with text + HTML versions
- Includes applicant's UUID for tracking
- Called automatically on successful form submission

**`EmailComposeView.form_valid()`** (`dashboard/views.py`)
- Renders template: `emails/base_email.html`
- Sends via BCC for recipient privacy
- Creates `SentEmail` record for audit trail
- Handles exceptions with try/except and logs errors

### DNS Configuration (Namecheap)
Required TXT records for email deliverability:

| Type | Host | Value |
|------|------|-------|
| TXT | @ | `v=spf1 +ip4:75.102.22.82 +include:_spf.mailchannels.net +a +mx ~all` |
| TXT | default._domainkey | `v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQE...` (from cPanel) |
| TXT | _dmarc | `v=DMARC1; p=none; rua=mailto:info@asncol.com` |

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

# Test email sending
python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Message', 'info@asncol.com', ['test@example.com'])
"
```

## Environment Variables (.env)

```env
# Core Django
DEBUG=True
SECRET_KEY=<your-secret-key>
ALLOWED_HOSTS=127.0.0.1,localhost

# CSRF (required for production with HTTPS)
CSRF_TRUSTED_ORIGINS=https://asncol.com,https://www.asncol.com

# PostgreSQL Database
DB_NAME=asnc_db
DB_USER=postgres
DB_PASSWORD=<password>
DB_HOST=localhost
DB_PORT=5432

# AWS S3 (Production only, when DEBUG=False)
S3_CLIENT_PREFIX=asnc

# Email SMTP Configuration
EMAIL_HOST=bh8928.banahosting.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=info@asncol.com
EMAIL_HOST_PASSWORD=<email-password>
DEFAULT_FROM_EMAIL=info@asncol.com
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
- Email templates: `templates/emails/` and `admissions/templates/admissions/emails/`
- Use `{% load crispy_forms_tags %}` for forms
- CSS variables defined in base.html:
  - `--asnc-navy: #1B2A41`
  - `--asnc-blue: #213a5c`
  - `--asnc-gold: #f4c343`
  - `--asnc-bg: #F5F7FA`

### Static Files
- Images: `static/images/`
- Favicon: `static/images/icon_asnc.png`
- Use `{% static 'path' %}` template tag
- Media uploads go to `media/` directory
- Production static URL: `https://vadomdata.s3.amazonaws.com/asnc/static/`

### Template Files (25 total)
```
templates/
├── base.html
├── robots.txt
├── 400.html, 403.html, 403_csrf.html, 404.html, 500.html
├── emails/
│   └── base_email.html
└── website/
    └── powerpoint_template.html

website/templates/website/
├── home.html
├── about.html
└── events.html

admissions/templates/admissions/
├── application_form.html
├── application_success.html
└── emails/
    └── application_received.html

dashboard/templates/dashboard/
├── base_dashboard.html
├── login.html
├── home.html
├── application_list.html
├── application_detail.html
├── featured_members/
│   ├── list.html
│   ├── form.html
│   └── confirm_delete.html
└── emails/
    ├── compose.html
    ├── history.html
    └── detail.html
```

### Frontend Assets (CDN)
- Bootstrap 5.3.0 (CSS + JS)
- Bootstrap Icons
- Google Fonts: Outfit
- anime.js - Used for scroll animations on homepage
- Flaticon CDN - Social media icons in emails

## SEO Implementation

### Meta Tags (base.html)
- Dynamic `<title>` with block override
- Meta description, keywords, robots, language, geo tags
- Canonical URL
- Open Graph tags (Facebook, LinkedIn)
- Twitter Card tags

### JSON-LD Structured Data
- Organization schema with name, logo, description
- Social media links (sameAs)
- Area served, founding date, knowsAbout
- Location: Bucaramanga, Santander, Colombia

### Sitemap (`/sitemap.xml`)
- Auto-generated via `django.contrib.sitemaps`
- Includes: home, about, events
- Configured in `website/sitemaps.py`

### robots.txt (`/robots.txt`)
- Allows all public pages
- Blocks: `/admin/`, `/portal/`, `/media/applications/`
- References sitemap URL

## Custom Error Pages

All error pages have consistent ASNC branding:

| File | Error | Description |
|------|-------|-------------|
| `400.html` | Bad Request | Purple accent, question icon |
| `403.html` | Forbidden | Red accent, shield icon |
| `403_csrf.html` | CSRF Failed | Red accent, tips for resolution |
| `404.html` | Not Found | Gold accent, search icon |
| `500.html` | Server Error | Orange accent, warning icon |

## Forms

### MembershipApplicationForm (`admissions/forms.py`)
Public-facing membership application form.

**Included Fields:**
- `first_name`, `last_name`, `email`, `phone`, `profession`, `contribution_statement`

**NOT Included (model-only fields):**
- `current_job`, `institution`, `linkedin_url`, `cv_file`
- These can be added later by admin or in future form versions

**Widgets:** TextInput, EmailInput, Textarea with `form-control-lg` Bootstrap classes

### FeaturedMemberForm (`dashboard/forms.py`)
Dashboard form for managing featured members.

**Fields:** full_name, photo, association_position, profession, professional_trajectory, linkedin_url, is_active, display_order

**Widgets:** TextInput, FileInput, URLInput, CheckboxInput, NumberInput

### EmailComposeForm (`dashboard/forms.py`)
Email composition form with multiple recipient types.

**Fields:**
- `recipient_type` (RadioSelect): 'manual', 'users', 'applicants'
- `manual_emails` (Textarea): For manual email entry
- `selected_users` (CheckboxSelectMultiple): System users
- `selected_applicants` (CheckboxSelectMultiple): Approved applicants
- `subject`, `message`

**Methods:**
- `clean()`: Validates that recipients are selected based on recipient_type
- `get_recipients()`: Returns list of email addresses based on selection

## Dashboard Features

### Sidebar Structure
```
PRINCIPAL
├── Dashboard (dashboard_home)

GESTIÓN ACADÉMICA
├── Solicitudes (application_list)
└── Directorio Oficial (placeholder)

CONTENIDO WEB
└── Asociados Destacados (featured_member_list)

COMUNICACIONES
└── Correos (email_history)

ADMINISTRACIÓN
├── Pagos y Cartera (placeholder)
└── Configuración (placeholder)
```

### Email Module
- **Compose** (`/portal/correos/redactar/`):
  - 3 recipient types: manual, users, applicants
  - Live preview panel
  - Auto-applies ASNC branded template
- **History** (`/portal/correos/`):
  - Paginated list (20 per page)
  - Shows: date, subject, recipient count, status
- **Detail** (`/portal/correos/<id>/`):
  - Full message content
  - Recipient list
  - Error details if failed

## Views Summary

### Website App
- `HomeView` (TemplateView) - Public homepage
- `AboutView` (ListView) - About page with FeaturedMembers
- `EventsView` (TemplateView) - Events page (under construction)
- `PowerPointTemplateView` (TemplateView) - ASNC presentation template

### Admissions App
- `ApplicationCreateView` (CreateView) - Membership form
- `ApplicationSuccessView` (TemplateView) - Confirmation
- `ApplicationListView` (LoginRequiredMixin, ListView)
- `ApplicationDetailView` (LoginRequiredMixin, DetailView)
- `change_application_status()` - Status change function
- `send_application_email()` - Sends confirmation email

### Dashboard App
- `CustomLoginView` (LoginView) - Email-based login
- `DashboardHomeView` (LoginRequiredMixin, TemplateView) - KPIs
- `FeaturedMemberListView` - List featured members
- `FeaturedMemberCreateView` - Create new member
- `FeaturedMemberUpdateView` - Edit member
- `FeaturedMemberDeleteView` - Delete confirmation
- `EmailComposeView` (FormView) - Compose and send emails
- `EmailHistoryView` (ListView) - Email history
- `EmailDetailView` (DetailView) - Email detail

## Storage Configuration

### Development (DEBUG=True)
- Static files: `/static/` served locally
- Media files: `/media/` served locally

### Production (DEBUG=False)
- Uses AWS S3 via django-storages
- Bucket: `vadomdata`
- Region: `us-east-1`
- Static: `asnc/static/`
- Media: `asnc/media/`
- Logo URL for emails: `https://vadomdata.s3.amazonaws.com/asnc/static/images/asnc_logo_full.png`

## Security Notes

- CSRF protection enabled on all forms
- CSRF_TRUSTED_ORIGINS configured for production HTTPS
- Custom error pages don't expose sensitive information
- Sensitive data in `.env` file (not committed)
- Protected views use Django's authentication mixins
- robots.txt blocks admin and portal paths
- Email recipients sent via BCC for privacy

## Email Best Practices

To avoid spam filters:
1. **DNS Authentication**: SPF, DKIM, DMARC configured
2. **Sending Limits**: Max 50-100 emails/day initially
3. **Content**: Avoid spam words, balance text/images
4. **List Hygiene**: Only send to consented recipients
5. **Headers**: Proper From/Reply-To addresses

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
| Pillow | 11.1.0 | Image processing |

## Migration History

### users
- `0001_initial.py` - Creates User model with email as unique USERNAME_FIELD

### admissions
- `0001_initial.py` (2025-12-20) - Creates MembershipApplication model
- `0002_add_contribution_statement.py` (2026-01-16) - Adds contribution_statement field, cv_file blank=True
- `0003_alter_membershipapplication_phone.py` (2026-01-24) - Makes phone field optional (blank=True)

### website
- `0001_initial.py` (2026-01-17) - Creates FeaturedMember model

### dashboard
- `0001_initial.py` (2026-01-25) - Creates SentEmail model

## Static Files Inventory

**Location:** `static/images/`

| File | Purpose |
|------|---------|
| `asnc_logo_full.png` | Main ASNC logo (used in emails, header) |
| `icon_asnc.png` | Favicon |
| `og-image.png` | Open Graph social sharing image |
| `about.png` | About page header image |
| `hero_agriculture.jpg` | Homepage hero carousel |
| `hero_energy.jpg` | Homepage hero carousel |
| `hero_medicine.jpg` | Homepage hero carousel |
| `nuclenergy_logo.png` | Partner logo |
| `nuclenergy_logo_blanco.png` | Partner logo (white version) |
| `super_nuclenergy.png` | Partner/sponsor image |
| `supernuc.png` | Partner/sponsor image |

## Future Enhancements (TODO)

- [ ] REST API endpoints
- [ ] Member directory
- [ ] Payment integration
- [ ] Auto-create user account on approval
- [ ] Role-based access control
- [ ] Two-factor authentication
- [ ] Celery for async email queue
- [ ] Migrate to Amazon SES for better deliverability
- [ ] Events management system (replace placeholder)
- [ ] Search/filter functionality on dashboard
- [ ] Email open/click tracking
- [ ] Bulk email with rate limiting
