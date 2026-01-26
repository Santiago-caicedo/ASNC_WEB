# CLAUDE.md - ASNC Platform

## Project Overview

This is the **ASNC Platform** (Asociación Nuclear Colombiana) - a Django 6.0 web application for managing membership admissions, digital member cards, email communications, and providing portals for both administrators and members.

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
- **PDF Generation**: ReportLab
- **QR Codes**: qrcode[pil]
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
│       └── emails/              # HTML email templates
├── carnets/                     # Digital member card system (NEW)
│   ├── models.py                # MemberCard, CardVerification
│   ├── views.py                 # Card generation, verification, photo upload
│   ├── utils.py                 # PDF and QR code generation
│   ├── forms.py                 # PhotoUploadForm
│   └── templates/carnets/       # Card templates and emails
├── members/                     # Member portal for associates (NEW)
│   ├── views.py                 # Member dashboard, card view, profile
│   └── templates/members/       # Member portal templates
├── dashboard/                   # Admin portal for committee members
│   ├── models.py                # SentEmail model (email history)
│   ├── forms.py                 # FeaturedMemberForm, EmailComposeForm
│   └── templates/dashboard/     # Dashboard templates
│       ├── featured_members/    # CRUD templates for featured members
│       ├── directory/           # Official member directory (NEW)
│       └── emails/              # Email compose, history, detail templates
├── website/                     # Public-facing pages
│   ├── templates/website/       # Home, About, Events, PowerPoint template
│   ├── models.py                # FeaturedMember model
│   ├── views.py                 # HomeView, AboutView, EventsView
│   └── sitemaps.py              # SEO sitemaps
├── templates/                   # Base templates
│   ├── base.html                # Main layout with SEO meta tags
│   ├── robots.txt               # SEO robots file
│   ├── emails/                  # Reusable email templates
│   │   └── base_email.html      # ASNC branded email template
│   └── 400.html, 403.html, 404.html, 500.html  # Error pages
├── static/images/               # Static assets (logos, hero images, favicon)
├── media/                       # User uploads (CVs, member photos, card photos)
├── requirements.txt             # Python dependencies
└── .env                         # Environment variables (not in git)
```

## Django Apps

| App | Purpose |
|-----|---------|
| `users` | Custom User model extending AbstractUser, email-based auth |
| `admissions` | MembershipApplication model, form submission, email notifications, user creation on approval |
| `carnets` | Digital member cards with QR verification, PDF generation, photo upload system |
| `members` | Member portal for associates to view their card, profile, and download PDF |
| `dashboard` | Protected admin views, KPIs, application management, directory, featured members CRUD, email mailing |
| `website` | Public pages: homepage, about, events, PowerPoint template |

## Key Models

### User (`users/models.py`)
- Extends `AbstractUser`
- `email` is the primary authentication field (unique)
- Standard Django auth fields
- OneToOne relation to `MemberCard` (via `member_card` related_name)

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

### MemberCard (`carnets/models.py`) - NEW
Digital member card for ASNC associates.

**Fields:**
- `uuid`: UUIDField - Unique identifier for verification URL
- `card_number`: CharField - Format: ASNC-YYYY-NNNN (e.g., ASNC-2026-0001)
- `user`: OneToOneField → User
- `application`: OneToOneField → MembershipApplication (nullable)
- `photo`: ImageField - Member photo (upload to `carnets/photos/`)
- `category`: FOUNDER | ASSOCIATE
- `issue_date`: DateField - Card issue date
- `expiry_date`: DateField - Default: Dec 31 of issue year
- `status`: PENDING_PHOTO | ACTIVE | EXPIRED | SUSPENDED | CANCELLED
- `photo_token`: UUIDField - Unique token for photo upload link
- `photo_token_used`: BooleanField
- `issued_by`: ForeignKey → User (admin who issued)
- `suspension_reason`: TextField
- `created_at`, `updated_at`: Timestamps

**Status Choices:**
| Code | Label |
|------|-------|
| PENDING_PHOTO | Pendiente de Foto |
| ACTIVE | Activo |
| EXPIRED | Expirado |
| SUSPENDED | Suspendido |
| CANCELLED | Cancelado |

**Category Choices:**
| Code | Label |
|------|-------|
| FOUNDER | Fundador |
| ASSOCIATE | Asociado |

**Methods:**
- `generate_card_number()`: Class method to generate next sequential number
- `is_valid`: Property to check if card is active and not expired
- `full_name`: Property to get cardholder's name
- `get_verification_url()`: Returns public verification URL

### CardVerification (`carnets/models.py`) - NEW
Log of card verification scans (QR code scans).

**Fields:**
- `card`: ForeignKey → MemberCard
- `verified_at`: DateTimeField (auto)
- `ip_address`: GenericIPAddressField
- `user_agent`: TextField

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

## URL Structure

```
# Public Website
/                              → Homepage (HomeView)
/quienes-somos/                → About page with team (AboutView)
/eventos/                      → Events page - under construction (EventsView)
/recursos/plantilla-presentacion/ → PowerPoint template page
/solicitud/                    → Membership application form
/gracias/                      → Application success page

# Public Card Verification (NEW)
/verificar/<uuid>/             → Public card verification page (QR scan destination)

# Card Photo Upload (NEW - no login required, token-based)
/carnes/subir-foto/<token>/    → Photo upload form for new members

# SEO
/sitemap.xml                   → Dynamic XML sitemap
/robots.txt                    → Robots file for crawlers

# Member Portal (NEW - requires login, regular users)
/mi-portal/                    → Member dashboard
/mi-portal/carnet/             → View my digital card
/mi-portal/carnet/descargar/   → Download card as PDF
/mi-portal/perfil/             → View/edit my profile

# Admin Dashboard (Protected - staff/superuser only)
/portal/                       → Dashboard home with KPIs
/portal/solicitudes/           → Application list
/portal/solicitudes/<id>/      → Application detail
/portal/solicitudes/<id>/cambiar-estado/<status>/  → Change status

# Directory (NEW - Protected)
/portal/directorio/            → Official member directory
/portal/directorio/<id>/       → Member expediente (detailed record)

# Featured Members CRUD (Protected)
/portal/asociados-destacados/              → List featured members
/portal/asociados-destacados/nuevo/        → Create new member
/portal/asociados-destacados/<id>/editar/  → Edit member
/portal/asociados-destacados/<id>/eliminar/ → Delete member

# Email Module (Protected)
/portal/correos/               → Email history list
/portal/correos/redactar/      → Compose new email
/portal/correos/<id>/          → Email detail view

# Authentication
/acceso/                       → Login page
/salir/                        → Logout

# Password Management
/password/set/<uidb64>/<token>/ → Set password (first time)
/password/reset/               → Password reset request
/password/reset/done/          → Reset email sent
/password/reset/<uidb64>/<token>/ → Reset password form
/password/reset/complete/      → Reset complete

# Admin
/admin/                        → Django admin
```

## Django Admin Configuration

All models are registered with full-featured admin interfaces:

### UserAdmin (`users/admin.py`)
- List: email, full name, role badge (Superadmin/Staff/Usuario), card badge, active status, date joined
- Filters: is_staff, is_superuser, is_active, date_joined
- Search: email, first_name, last_name, username

### MemberCardAdmin (`carnets/admin.py`)
- List: card_number, user name, category badge, status colored, expiry date, photo thumbnail, created_at
- Filters: status, category, issue_date, expiry_date
- Search: card_number, user names, email, uuid
- Actions: Activate, Suspend, Mark as Expired (bulk)
- Fieldsets: Identification, Card Data, Validity, Administration, Photo Token, Audit

### CardVerificationAdmin (`carnets/admin.py`)
- List: card, verified_at, ip_address
- Read-only (verifications are created automatically)
- Date hierarchy by verified_at

### MembershipApplicationAdmin (`admissions/admin.py`)
- List: full_name, email, profession, status colored, CV link, created_at
- Filters: status, created_at, profession
- Actions: Approve (sends notification), Reject

### FeaturedMemberAdmin (`website/admin.py`)
- List: photo thumbnail, full_name, position, profession, active badge, display_order
- Editable: display_order (inline)
- Filters: is_active, created_at

### SentEmailAdmin (`dashboard/admin.py`)
- List: subject, sent_by, recipients_count, success badge, sent_at
- Read-only (emails are sent through dashboard)
- Date hierarchy by sent_at

## Carnets System (Digital Member Cards)

### Card Generation Flow
```
Application APPROVED → Admin clicks "Vincular y Crear Usuario"
    → User created with unusable password
    → Application status = COMPLETED
    → Admin clicks "Generar Carné" from expediente
    → MemberCard created with status = PENDING_PHOTO
    → Email sent to member with photo upload link
    → Member uploads photo via unique token link
    → Card status = ACTIVE
    → Email sent confirming card is ready
    → Member can view/download card at /mi-portal/carnet/
```

### PDF Generation (`carnets/utils.py`)
- Uses ReportLab for PDF creation
- Card dimensions: 160mm x 100mm (large format)
- Features:
  - ASNC branded header with logo
  - Gold header bar with "CARNET DE ASOCIADO"
  - Member photo (38mm x 50mm)
  - Name, card number, category
  - Issue and expiry dates
  - QR code for verification
  - Information boxes below card
  - Verification section with full URL
  - Footer with contact info

### QR Code Generation (`carnets/utils.py`)
- Uses qrcode library with PIL
- Encodes verification URL
- Size: 150px, error correction level M

### Key Functions in `carnets/utils.py`:
- `generate_qr_code(data, size)` - Creates QR code image
- `get_verification_url(card)` - Returns full verification URL
- `generate_card_pdf(card)` - Creates PDF with card
- `send_photo_request_email(card)` - Sends email requesting photo
- `send_card_ready_email(card)` - Sends email when card is active

## Access Control

### StaffRequiredMixin
Used in dashboard and admin views to restrict access to staff/superusers only.

```python
class StaffRequiredMixin(UserPassesTestMixin):
    login_url = '/acceso/'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('/mi-portal/')  # Regular users go to member portal
        return super().handle_no_permission()
```

### Portal Access:
- `/portal/` - Staff/Superuser only (admin dashboard)
- `/mi-portal/` - Any authenticated user (member portal)
- `/admin/` - Superuser only (Django admin)

## Email System

### SMTP Configuration
- **Host**: bh8928.banahosting.com (BanaHosting/MailChannels)
- **Port**: 465 (SSL)
- **From**: info@asncol.com

### Email Templates
```
templates/emails/
└── base_email.html              # ASNC branded template

admissions/templates/admissions/emails/
├── application_received.html    # Confirmation of application
├── application_approved.html    # Welcome email on approval
├── application_rejected.html    # Rejection notification
└── set_password.html            # Password setup link

carnets/templates/carnets/emails/
├── solicitar_foto.html          # Request photo upload
└── carne_listo.html             # Card ready notification
```

### Email Functions
| Function | Location | Purpose |
|----------|----------|---------|
| `send_application_email()` | admissions/views.py | Confirmation on form submit |
| `send_approval_email()` | admissions/views.py | Welcome on approval |
| `send_set_password_email()` | admissions/views.py | Password setup link |
| `send_rejection_email()` | admissions/views.py | Rejection notification |
| `send_photo_request_email()` | carnets/utils.py | Request card photo |
| `send_card_ready_email()` | carnets/utils.py | Card activation notification |

## Environment Variables (.env)

```env
# Core Django
DEBUG=True
SECRET_KEY=<your-secret-key>
ALLOWED_HOSTS=127.0.0.1,localhost

# Site URL for emails (NEW)
SITE_URL=http://127.0.0.1:8000        # Development
# SITE_URL=https://www.asncol.com     # Production

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

# Check for issues
python manage.py check

# Show migration status
python manage.py showmigrations
```

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
| qrcode[pil] | 7.4.2 | QR code generation (NEW) |
| reportlab | 4.1.0 | PDF generation (NEW) |

## Migration History

### users
- `0001_initial.py` - Creates User model with email as unique USERNAME_FIELD

### admissions
- `0001_initial.py` (2025-12-20) - Creates MembershipApplication model
- `0002_add_contribution_statement.py` (2026-01-16) - Adds contribution_statement field
- `0003_alter_membershipapplication_phone.py` (2026-01-24) - Makes phone optional

### carnets (NEW)
- `0001_initial.py` (2026-01-25) - Creates MemberCard and CardVerification models

### website
- `0001_initial.py` (2026-01-17) - Creates FeaturedMember model

### dashboard
- `0001_initial.py` (2026-01-25) - Creates SentEmail model

## Views Summary

### Website App
- `HomeView` (TemplateView) - Public homepage
- `AboutView` (ListView) - About page with FeaturedMembers
- `EventsView` (TemplateView) - Events page (under construction)
- `PowerPointTemplateView` (TemplateView) - ASNC presentation template

### Admissions App
- `ApplicationCreateView` (CreateView) - Membership form
- `ApplicationSuccessView` (TemplateView) - Confirmation
- `ApplicationListView` (StaffRequiredMixin, ListView)
- `ApplicationDetailView` (StaffRequiredMixin, DetailView)
- `change_application_status()` - Status change with user creation on COMPLETED

### Carnets App (NEW)
- `VerificarCarnetView` (TemplateView) - Public QR verification page
- `SubirFotoView` (FormView) - Photo upload (token-based, no login)
- `GenerarCarnetView` (StaffRequiredMixin, View) - Admin generates card

### Members App (NEW)
- `MemberDashboardView` (LoginRequiredMixin, TemplateView) - Member home
- `MemberCardView` (LoginRequiredMixin, TemplateView) - View my card
- `MemberCardDownloadView` (LoginRequiredMixin, View) - Download PDF
- `MemberProfileView` (LoginRequiredMixin, TemplateView) - View profile

### Dashboard App
- `CustomLoginView` (LoginView) - Redirects based on user role
- `DashboardHomeView` (StaffRequiredMixin, TemplateView) - KPIs
- `DirectoryListView` (StaffRequiredMixin, ListView) - Member directory
- `DirectoryDetailView` (StaffRequiredMixin, DetailView) - Member expediente
- `FeaturedMemberListView` - List featured members
- `FeaturedMemberCreateView` - Create new member
- `FeaturedMemberUpdateView` - Edit member
- `FeaturedMemberDeleteView` - Delete confirmation
- `EmailComposeView` (FormView) - Compose and send emails
- `EmailHistoryView` (ListView) - Email history
- `EmailDetailView` (DetailView) - Email detail

## Template Files

```
templates/
├── base.html
├── robots.txt
├── 400.html, 403.html, 403_csrf.html, 404.html, 500.html
└── emails/
    └── base_email.html

website/templates/website/
├── home.html
├── about.html
└── events.html

admissions/templates/admissions/
├── application_form.html
├── application_success.html
└── emails/
    ├── application_received.html
    ├── application_approved.html
    ├── application_rejected.html
    └── set_password.html

carnets/templates/carnets/           # NEW
├── verificar.html                   # Public verification page
├── subir_foto.html                  # Photo upload form
├── subir_foto_exito.html            # Upload success
└── emails/
    ├── solicitar_foto.html
    └── carne_listo.html

members/templates/members/           # NEW
├── base_members.html                # Member portal base
├── dashboard.html                   # Member home
├── card.html                        # View my card
└── profile.html                     # My profile

dashboard/templates/dashboard/
├── base_dashboard.html
├── login.html
├── home.html
├── application_list.html
├── application_detail.html
├── directory/                       # NEW
│   ├── list.html
│   └── detail.html
├── featured_members/
│   ├── list.html
│   ├── form.html
│   └── confirm_delete.html
└── emails/
    ├── compose.html
    ├── history.html
    └── detail.html
```

## Dashboard Sidebar Structure

```
PRINCIPAL
├── Dashboard (dashboard_home)

GESTIÓN DE ASOCIADOS
├── Solicitudes (application_list)
└── Directorio Oficial (directory_list) ← NEW

CARNETS DIGITALES                    ← NEW section
└── (Managed via Directory expediente)

CONTENIDO WEB
└── Asociados Destacados (featured_member_list)

COMUNICACIONES
└── Correos (email_history)

ADMINISTRACIÓN
├── Pagos y Cartera (placeholder)
└── Configuración (placeholder)
```

## Code Conventions

### Python/Django
- Use Spanish for user-facing content (labels, messages, templates)
- Use English for code (variable names, comments, docstrings)
- Follow Django conventions for model/view naming
- Use Class-Based Views for complex logic
- Use `StaffRequiredMixin` for admin-only views
- Use `LoginRequiredMixin` for member-only views
- Forms use `crispy_forms` with Bootstrap 5
- Use `mark_safe()` for static HTML in admin (Django 6.0 requirement)
- Use `format_html()` only when formatting dynamic content

### CSS Variables
```css
--asnc-navy: #1B2A41
--asnc-blue: #213a5c
--asnc-gold: #f4c343
--asnc-bg: #F5F7FA
```

## Security Notes

- CSRF protection enabled on all forms
- CSRF_TRUSTED_ORIGINS configured for production HTTPS
- Custom error pages don't expose sensitive information
- Sensitive data in `.env` file (not committed)
- Protected views use Django's authentication mixins
- Photo upload uses unique UUID tokens (not user auth)
- robots.txt blocks admin, portal, and media paths
- Email recipients sent via BCC for privacy
- Password reset tokens with expiration

## Deployment Checklist

When deploying new changes:

```bash
# 1. Install new dependencies
pip install -r requirements.txt

# 2. Run migrations
python manage.py makemigrations
python manage.py migrate

# 3. Collect static files
python manage.py collectstatic --noinput

# 4. Update .env with SITE_URL
SITE_URL=https://www.asncol.com

# 5. Restart server
sudo systemctl restart gunicorn  # or your server process
```

## Future Enhancements (TODO)

- [x] ~~Member directory~~ (Implemented)
- [x] ~~Auto-create user account on approval~~ (Implemented)
- [x] ~~Digital member cards with QR~~ (Implemented)
- [x] ~~Role-based access control~~ (Implemented)
- [ ] REST API endpoints
- [ ] Payment integration
- [ ] Two-factor authentication
- [ ] Celery for async email queue
- [ ] Migrate to Amazon SES for better deliverability
- [ ] Events management system (replace placeholder)
- [ ] Email open/click tracking
- [ ] Bulk email with rate limiting
- [ ] Card renewal workflow
- [ ] Member self-service profile editing
