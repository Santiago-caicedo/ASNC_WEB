# CLAUDE.md - ASNC Platform

## Project Overview

This is the **ASNC Platform** (Asociación Nuclear Colombiana) - a Django 6.0 web application for managing membership admissions, digital member cards, email communications, and providing portals for both administrators and members.

**Official Domain:** www.asncol.com
**Contact Email:** info@asncol.com
**Location:** Bucaramanga, Santander, Colombia

**Official Social Media:**
- **LinkedIn:** https://www.linkedin.com/company/asociaci%C3%B3n-nuclear-colombiana/
- **Instagram:** https://www.instagram.com/asncol_oficial
- **Facebook:** https://www.facebook.com/share/1BhF3tqKT7/
- **X (Twitter):** https://x.com/asncol_oficial

**Developed by:** Vadom Data Consulting (https://vadomdata.com/)

## Branches & Scope (IMPORTANT)

The repository has **two branches**:

| Branch | Contents |
|--------|----------|
| `main` | Production platform. Everything documented here lives in `main` **except** the Virtual Classroom. |
| `aula-virtual` | **Work-in-progress LMS** ("Aula Virtual" / `capacitaciones` app). Branched from `main`; will be merged later. |

**Why the split:** the `capacitaciones` LMS (courses, classes, quizzes, certificates, virtual classroom) was moved off `main` so day-to-day platform work continues without it. **Do NOT add capacitaciones code to `main`** — work on the `aula-virtual` branch for anything LMS-related. The `capacitaciones/` folder may still exist physically on `main` but only as ignored `.pyc` files; it is not in `INSTALLED_APPS` on `main`.

Known issues already identified on `aula-virtual` (to fix before merging): AJAX attendance breaks in production because `CSRF_COOKIE_HTTPONLY=True` and the JS reads the cookie; async attendance only auto-tracks for S3 video files (not YouTube/Vimeo); open-ended quiz questions have no manual grading UI; certificate issuance does not enforce minimum attendance/grade.

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
- **Excel Export**: XlsxWriter (styled `.xlsx` exports of applications)
- **QR Codes**: qrcode (with PIL support)
- **Date Utilities**: python-dateutil (relativedelta for membership duration)
- **SEO**: django.contrib.sitemaps
- **Analytics**: Google Analytics 4 (gtag.js) - ID: G-1H2FNJ5PB8
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
├── carnets/                     # Digital member card system
│   ├── models.py                # MemberCard, CardVerification
│   ├── views.py                 # Card generation, verification, photo upload
│   ├── utils.py                 # PDF and QR code generation
│   ├── forms.py                 # PhotoUploadForm, GenerateCardForm, CardSuspendForm, CardRenewForm
│   └── templates/carnets/       # Card templates and emails
├── members/                     # Member portal for associates
│   ├── views.py                 # Member dashboard, card view, profile, password change
│   ├── forms.py                 # ProfileEditForm
│   └── templates/members/       # Member portal templates
├── dashboard/                   # Admin portal for committee members
│   ├── models.py                # SentEmail model (email history)
│   ├── forms.py                 # FeaturedMemberForm, EmailComposeForm
│   ├── templatetags/            # Custom template tags
│   │   └── dashboard_extras.py  # get_item filter for dict access
│   └── templates/dashboard/     # Dashboard templates
│       ├── featured_members/    # CRUD templates for featured members
│       ├── directory/           # Official member directory
│       └── emails/              # Email compose, history, detail templates
├── website/                     # Public-facing pages
│   ├── templates/website/       # Home, About (comités), Events, News, PowerPoint
│   ├── models.py                # FeaturedMember, NewsArticle models
│   ├── views.py                 # HomeView, AboutView, EventsView, News views
│   └── sitemaps.py              # SEO sitemaps
├── convocatorias/               # Public calls with dynamic form builder
│   ├── models.py                # Convocatoria, ConvocatoriaField, Submission, SubmissionFile
│   ├── views.py                 # Public (list/detail/submit) + admin CRUD/export
│   ├── urls.py / admin_urls.py  # Public routes + /portal/convocatorias/ routes
│   └── templates/convocatorias/ # public/ and admin/ templates
# capacitaciones/                # LMS — lives on the `aula-virtual` branch, NOT main
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
| `users` | Custom User model extending AbstractUser, email-based auth, role system (`role`, `can_edit_news`) |
| `admissions` | MembershipApplication model, public form, email notifications, user creation on approval, internal management (contactado/sector/notes), CSV+Excel export |
| `carnets` | Digital member cards with QR verification, PDF generation, photo upload system |
| `members` | Member portal for associates: dashboard, card view/download, profile view/edit, password change, membership duration |
| `dashboard` | Protected admin views, KPIs, application management, directory, featured members CRUD, **news CRUD**, **user/role management**, email mailing |
| `website` | Public pages: homepage, about (with comités), events, **news (blog)**, PowerPoint template |
| `convocatorias` | Public calls (convocatorias) with a dynamic form builder, submissions, file uploads and CSV export |
| `capacitaciones` | **LMS / Aula Virtual — on the `aula-virtual` branch only, NOT in `main`** |

## Key Models

### User (`users/models.py`)
- Extends `AbstractUser`
- `email` is the primary authentication field (unique)
- `role`: CharField (choices MEMBER | ADMIN, default MEMBER, db_index) — high-level role
- `can_edit_news`: BooleanField - grants access to news CRUD without full admin
- `phone`: CharField - Contact phone number
- `profession`: CharField - Professional title
- `current_job`: CharField - Current position
- `institution`: CharField - Company/Institution
- `linkedin_url`: URLField - LinkedIn profile
- `bio`: TextField - Professional biography
- Standard Django auth fields
- OneToOne relation to `MemberCard` (via `member_card` related_name)
- `is_admin` property: `is_superuser or role == ADMIN`
- `is_news_editor` property: `can_edit_news`
- `profile_completion` property: Calculates profile completion percentage (0-100%)

**Role system & access (5 effective user types):**
| Type | Determined by | Lands on |
|------|---------------|----------|
| Superadmin | `is_superuser` | `/admin/` + everything |
| Admin | `role='ADMIN'` (+staff) | `/portal/` |
| News editor | `can_edit_news=True` | `/portal/noticias/` |
| Associate (member) | `role='MEMBER'` | `/mi-portal/` |
| Course participant | has `participante_capacitacion` (LMS branch) | `/capacitaciones/aula/` |

> Note: `NEWS_EDITOR` was a former `role` value, deprecated in favor of the independent `can_edit_news` flag (migration `users/0004`).

**Access mixins (`dashboard/views.py`):** `StaffRequiredMixin` (any staff), `AdminRequiredMixin` (full admin; also defined in `admissions/views.py`), `NewsEditorRequiredMixin` (news editors or admins).

**Profile Completion Calculation:**
```python
@property
def profile_completion(self):
    fields = ['first_name', 'last_name', 'phone', 'profession',
              'current_job', 'institution', 'linkedin_url', 'bio']
    filled = sum(1 for f in fields if getattr(self, f, None))
    return int((filled / len(fields)) * 100)
```

**Completion Level Badges (in profile.html):**
| Percentage | Badge | Color | Message |
|------------|-------|-------|---------|
| 100% | Completo | Green | "Tu perfil esta completo" |
| 75-99% | Casi listo | Gold | "Solo faltan algunos datos" |
| 50-74% | Buen avance | Blue | "Continua completando tu perfil" |
| < 50% | En progreso | Gray | "Completa tu informacion" |

### MembershipApplication (`admissions/models.py`)
- `uuid`: Unique identifier for tracking
- `first_name`, `last_name`, `email`, `phone` (optional)
- `profession`, `current_job`, `institution`, `linkedin_url`
- `contribution_statement`: TextField for applicant's motivation
- `cv_file`: FileField for CV uploads (to `applications/cvs/`)
- `status`: PENDING | REVIEW | APPROVED | REJECTED | COMPLETED
- `contactado`: BooleanField - committee contact flag (set in admin, not public)
- `sector`: CharField with fixed choices (set by the committee in the admin **after the contact call** — NOT shown on the public form)
- `admin_notes`: Internal committee notes (editable from the application detail)
- `created_at`, `updated_at`: Timestamps
- Ordering: `-created_at` (newest first)
- **Meta:** `verbose_name = 'Solicitud de Ingreso'`

**Sector Choices (fixed, admin-only):** NUCLEAR (Sector Nuclear), MINING (Sector Minero), OIL_GAS (Oil and Gas), ENERGY (Sector Energético), AGRO (Agroindustria / Alimentos), HEALTH (Sector Salud), ACADEMIA (Academia), REGULATORY (Sector Regulatorio), OTHER (Otros).

**Public form (`MembershipApplicationForm`)** collects only: first_name, last_name, email, phone, profession, contribution_statement (+ anti-bot honeypot/timestamp). `contactado`, `sector` and `admin_notes` are managed by the committee in the admin detail.

**Internal management & export:**
- The application list (`/portal/solicitudes/`) is **paginated (15/page)** and shows Sector + Contactado columns.
- The application detail has a "Gestión Interna del Comité" form (selector contactado, selector sector, notes textarea) saved via `update_application_admin`.
- Export of all applications to **CSV** (BOM UTF-8) and **Excel `.xlsx`** (XlsxWriter; colored header + status/contactado/sector cells, frozen header, autofilter) from the "Exportar" dropdown.

**Status Choices (Spanish labels):**
| Code | Label |
|------|-------|
| PENDING | Pendiente de Revisión |
| REVIEW | En Estudio |
| APPROVED | Aprobado |
| REJECTED | Rechazado |
| COMPLETED | Vinculado (Usuario Creado) |

### MemberCard (`carnets/models.py`)
Digital member card for ASNC associates.

**Fields:**
- `uuid`: UUIDField - Unique identifier for verification URL
- `card_number`: CharField - Format: ASNC-YYYY-NNNN (e.g., ASNC-2026-0001)
- `user`: OneToOneField → User (on_delete=PROTECT to prevent accidental deletion)
- `application`: OneToOneField → MembershipApplication (nullable)
- `photo`: ImageField - Member photo (upload to `carnets/photos/`)
- `category`: FOUNDER | ASSOCIATE
- `issue_date`: DateField - Card issue date
- `expiry_date`: DateField - Default: Dec 31 of issue year
- `status`: PENDING_PHOTO | ACTIVE | EXPIRED | SUSPENDED | CANCELLED
- `photo_token`: UUIDField - Unique token for photo upload link
- `photo_token_used`: BooleanField
- `photo_token_created_at`: DateTimeField - Token creation time for expiration control (72 hours)
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
- `generate_card_number()`: Class method to generate next sequential number (uses `select_for_update()` to prevent race conditions)
- `is_valid`: Property to check if card is active and not expired
- `full_name`: Property to get cardholder's name
- `get_verification_url()`: Returns public verification URL

### CardVerification (`carnets/models.py`)
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
- Note: the About page also renders a fixed set of **Comités** (visual only, no DB model).

### NewsArticle (`website/models.py`)
News/blog article shown publicly and managed by admins/news editors.
- `category`: CharField (ASSOCIATION = 'De la Asociación' | NUCLEAR = 'Temática Nuclear')
- `title`, `slug` (unique, auto-generated), `cover_image` (to `news/`)
- `excerpt`: TextField (max 300), `content`: TextField (HTML supported)
- `author`: ForeignKey → User (related_name `news_articles`)
- `is_published`: BooleanField, `published_at`: DateTimeField (auto-set on publish)
- `created_at`, `updated_at`: Timestamps

### Convocatoria models (`convocatorias/models.py`)
Public calls with a dynamic form builder.
- **Convocatoria**: uuid, title, slug, description, cover_image, is_active, `opens_at`/`closes_at`, `success_message`, created_by. Property `is_open` (active + within date window); `submissions_count`.
- **ConvocatoriaField**: dynamic form field — `field_type` (TEXT, TEXTAREA, EMAIL, PHONE, NUMBER, DATE, SELECT, CHECKBOX, FILE), `label`, `required`, `help_text`, `placeholder`, `options`, `order`.
- **ConvocatoriaSubmission**: uuid, `data` (JSONField), `submitted_at`, `ip_address`.
- **ConvocatoriaSubmissionFile**: file attachments for FILE-type fields.

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
/                              → Homepage (HomeView) - shows latest news
/quienes-somos/                → About page with team + comités (AboutView)
/eventos/                      → Events page - under construction (EventsView)
/noticias/                     → Public news list (NewsListView)
/noticias/<slug>/              → Public news detail (NewsDetailView)
/recursos/plantilla-presentacion/ → PowerPoint template page
/politica-de-privacidad/       → Privacy policy
/solicitud/                    → Membership application form (no sector field)
/gracias/                      → Application success page

# Convocatorias (Public)
/convocatorias/                → Public list of active calls
/convocatorias/<slug>/         → Detail + dynamic submission form
/convocatorias/<slug>/gracias/ → Submission success

# Public Card Verification
/verificar/<uuid>/             → Public card verification page (CardVerificationView)

# Card Photo Upload (no login required, token-based)
/carnes/subir-foto/<token>/       → Photo upload form (PhotoUploadView)
/carnes/subir-foto/<token>/exito/ → Photo upload success (PhotoUploadSuccessView)

# SEO
/sitemap.xml                   → Dynamic XML sitemap (home, about, events, application_create)
/robots.txt                    → Robots file for crawlers
/favicon.ico                   → Redirects to S3 static icon

# Member Portal (requires login, regular users)
/mi-portal/                    → Member dashboard (MemberDashboardView)
/mi-portal/carnet/             → View my digital card (MemberCardView)
/mi-portal/carnet/descargar/   → Download card as PDF (MemberCardDownloadView)
/mi-portal/perfil/             → View my profile (MemberProfileView)
/mi-portal/perfil/editar/      → Edit profile (MemberProfileEditView)
/mi-portal/cambiar-contrasena/ → Change password (MemberPasswordChangeView)
/mi-portal/contrasena-actualizada/ → Password changed confirmation

# Admin Dashboard (Protected - staff/superuser only)
/portal/                       → Dashboard home with KPIs
/portal/solicitudes/           → Application list (paginated 15/page)
/portal/solicitudes/exportar/csv/   → Export all applications to CSV
/portal/solicitudes/exportar/excel/ → Export all applications to styled .xlsx
/portal/solicitudes/<id>/      → Application detail
/portal/solicitudes/<id>/cambiar-estado/<status>/  → Change status
/portal/solicitudes/<id>/actualizar-gestion/ → Save contactado/sector/notes (update_application_admin)
/portal/solicitudes/<id>/reenviar-correo-contrasena/ → Resend password setup email

# Directory (Protected)
/portal/directorio/            → Official member directory
/portal/directorio/<id>/       → Member expediente (detailed record)

# Featured Members CRUD (Protected)
/portal/asociados-destacados/              → List featured members
/portal/asociados-destacados/nuevo/        → Create new member
/portal/asociados-destacados/<id>/editar/  → Edit member
/portal/asociados-destacados/<id>/eliminar/ → Delete member

# Carnets - Member URLs (requires login)
/mi-carne/                     → View my digital card (MyCardView)
/mi-carne/descargar/           → Download card as PDF (MyCardDownloadView)

# Carnets Dashboard (Protected - staff/superuser only)
/portal/carnes/                → Card list with filters
/portal/carnes/<id>/           → Card detail
/portal/carnes/<id>/suspender/ → Suspend card form
/portal/carnes/<id>/reactivar/ → Reactivate suspended card
/portal/carnes/<id>/renovar/   → Renew card expiry
/portal/carnes/<id>/reenviar-solicitud/ → Resend photo request email
/portal/carnes/estadisticas/   → Card statistics
/portal/solicitudes/<id>/generar-carne/ → Generate card from application

# News CRUD (Protected - news editors or admins)
/portal/noticias/              → News list
/portal/noticias/nueva/        → Create news
/portal/noticias/<id>/editar/  → Edit news
/portal/noticias/<id>/eliminar/ → Delete news

# User & Role Management (Protected - admins)
/portal/usuarios/              → User list
/portal/usuarios/<id>/         → User detail
/portal/usuarios/<id>/rol/     → Update user role

# Convocatorias (Protected - admins, under /portal/convocatorias/)
/portal/convocatorias/                        → List
/portal/convocatorias/nueva/                  → Create
/portal/convocatorias/<id>/ , /editar/ , /eliminar/  → Detail / edit / delete
/portal/convocatorias/<id>/campos/            → Manage dynamic fields
/portal/convocatorias/<id>/inscripciones/     → Submissions list
/portal/convocatorias/<id>/inscripciones/exportar/ → Export submissions CSV

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
- List: email, full name, role badge (Superadmin/Staff/Usuario), password status, card badge, active status, date joined
- Password status indicator: "Configurada" (green), "Configurada (sin login)" (blue), "Pendiente" (yellow)
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

### Application Approval Flow
```
Application PENDING → Admin reviews application
    → Admin clicks "Aprobar y Vincular"
    → User created with unusable password
    → Application status = COMPLETED
    → Single email sent with welcome message + password setup link
    → User configures password via link
    → User can access /mi-portal/
```

**Password Status Tracking:**
- Application list shows password status badge for COMPLETED applications:
  - Green key icon = Password configured
  - Yellow key icon = Password pending
- Application detail shows "Estado de la Cuenta" section with:
  - Password status (Configurada / Pendiente)
  - Last login date
  - "Reenviar Correo" button (only if password not configured)

### Card Generation Flow
```
Application COMPLETED → Admin clicks "Generar Carné" from expediente
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
- **S3 Compatible**: Uses `card.photo.open('rb')` instead of `card.photo.path` for AWS S3 storage compatibility
- Features:
  - Header with white background section for logo visibility
  - Gold accent bars at top and bottom of header
  - Navy subtitle bar with "CARNET DE ASOCIADO" in white
  - Member photo (38mm x 50mm)
  - Name, card number, category
  - Gold bar with ASNC logo (white rounded background for contrast)
  - Issue and expiry dates
  - QR code for verification
  - Information boxes below card
  - Verification section with full URL
  - Footer with contact info

**Photo Loading for S3:**
```python
if card.photo:
    with card.photo.open('rb') as photo_file:
        img = Image.open(photo_file)
        img.load()  # Force load before closing file
```

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
- **Sender Name**: "Asociación Nuclear Colombiana" (using `email.utils.formataddr`)

### Email Sender Formatting
Emails are sent with a proper display name using `formataddr`:
```python
from email.utils import formataddr
from_email = formataddr(('Asociación Nuclear Colombiana', settings.DEFAULT_FROM_EMAIL))
```

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
| `send_approval_email()` | admissions/views.py | Welcome + password setup link (unified email) |
| `send_set_password_email()` | admissions/views.py | Password setup link (for resending) |
| `send_rejection_email()` | admissions/views.py | Rejection notification |
| `send_photo_request_email()` | carnets/utils.py | Request card photo |
| `send_card_ready_email()` | carnets/utils.py | Card activation notification |

**Note:** When an application is approved, only ONE email is sent (`send_approval_email`) which includes both the welcome message and the password setup link. The `send_set_password_email` function is kept for resending the password link if needed.

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
| python-dateutil | 2.9.0 | Date calculations (relativedelta for membership duration) |
| Pillow | 11.1.0 | Image processing |
| qrcode | 8.2 | QR code generation |
| reportlab | 4.4.9 | PDF generation |
| XlsxWriter | 3.2.9 | Styled Excel (.xlsx) export of applications |

## Migration History

### users
- `0001_initial.py` - Creates User model with email as unique USERNAME_FIELD
- `0002_add_profile_fields.py` - Adds phone, profession, current_job, institution, linkedin_url, bio
- `0003_add_user_role.py` - Adds `role` field
- `0004_add_can_edit_news.py` - Adds `can_edit_news`; deprecates NEWS_EDITOR role value

### admissions
- `0001_initial.py` (2025-12-20) - Creates MembershipApplication model
- `0002_add_contribution_statement.py` (2026-01-16) - Adds contribution_statement field
- `0003_alter_membershipapplication_phone.py` (2026-01-24) - Makes phone optional
- `0004_membershipapplication_contactado.py` - Adds `contactado` flag
- `0005_membershipapplication_sector.py` - Adds `sector` field
- `0006`–`0009_alter_membershipapplication_sector.py` - Iterations of the fixed `sector` choices (final list incl. NUCLEAR)

### carnets
- `0001_initial.py` (2026-01-25) - Creates MemberCard and CardVerification models
- `0002_add_photo_token_expiration.py` (2026-01-29) - Adds photo_token_created_at field, changes user on_delete to PROTECT

### website
- `0001_initial.py` (2026-01-17) - Creates FeaturedMember model
- Adds `NewsArticle` model (news/blog) in a later migration

### dashboard
- `0001_initial.py` (2026-01-25) - Creates SentEmail model

### convocatorias
- `0001_initial.py` - Creates Convocatoria, ConvocatoriaField, Submission, SubmissionFile

> Migrations for `capacitaciones` live only on the `aula-virtual` branch.

## Views Summary

### Website App
- `HomeView` (TemplateView) - Public homepage (latest news)
- `AboutView` (ListView) - About page with FeaturedMembers + comités
- `EventsView` (TemplateView) - Events page (under construction)
- `PrivacyPolicyView` (TemplateView) - Privacy policy
- `PowerPointTemplateView` (TemplateView) - ASNC presentation template
- `NewsListView` / `NewsDetailView` - Public news (blog)

### Admissions App
- `ApplicationCreateView` (CreateView) - Membership form (no sector field)
- `ApplicationSuccessView` (TemplateView) - Confirmation
- `ApplicationListView` (AdminRequiredMixin, ListView) - Paginated, password status indicators, Sector + Contactado columns
- `ApplicationDetailView` (AdminRequiredMixin, DetailView) - User account status + internal management form
- `change_application_status()` - Status change with user creation on COMPLETED
- `update_application_admin()` - Save contactado / sector / admin notes
- `export_applications_csv()` / `export_applications_excel()` - Export all applications (CSV / styled .xlsx)
- `resend_password_email()` - Resend password setup email to users who haven't configured it
- Note: `AdminRequiredMixin` and `admin_required` decorator are defined here (admin-only access).

### Carnets App
- `CardVerificationView` (TemplateView) - Public QR verification page
- `PhotoUploadView` (FormView) - Photo upload (token-based, no login)
- `PhotoUploadSuccessView` (TemplateView) - Photo upload success page
- `MyCardView` (LoginRequiredMixin, TemplateView) - Member's card view
- `MyCardDownloadView` (LoginRequiredMixin, View) - Member's card PDF download
- `GenerateCardView` (StaffRequiredMixin, FormView) - Admin generates card
- `CardListView` (StaffRequiredMixin, ListView) - Dashboard card list with filters
- `CardDetailView` (StaffRequiredMixin, DetailView) - Card detail and actions
- `CardStatsView` (StaffRequiredMixin, TemplateView) - Card statistics dashboard
- `CardSuspendView` (StaffRequiredMixin, FormView) - Suspend a card with reason
- `CardRenewView` (StaffRequiredMixin, FormView) - Renew card expiry date
- `reactivate_card()` - Function view to reactivate suspended card
- `resend_photo_request()` - Function view to resend photo request email

### Members App
- `MemberLoginView` (LoginView) - Member login page
- `MemberDashboardView` (LoginRequiredMixin, TemplateView) - Member home with membership duration
- `MemberCardView` (LoginRequiredMixin, TemplateView) - View my card
- `MemberCardDownloadView` (LoginRequiredMixin, View) - Download PDF
- `MemberProfileView` (LoginRequiredMixin, TemplateView) - View profile with membership info
- `MemberProfileEditView` (LoginRequiredMixin, UpdateView) - Edit profile information
- `MemberPasswordChangeView` (LoginRequiredMixin, PasswordChangeView) - Change password
- `MemberPasswordChangeDoneView` (LoginRequiredMixin, TemplateView) - Password change confirmation

**Helper Functions:**
- `get_membership_duration(user)` - Calculate years/months as member
- `format_duration(years, months)` - Format duration in Spanish

**Forms (`members/forms.py`):**
- `ProfileEditForm` - Form for editing user profile (phone, profession, job, institution, LinkedIn, bio)

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
- `NewsListView` / `NewsCreateView` / `NewsUpdateView` / `NewsDeleteView` (NewsEditorRequiredMixin) - News CRUD
- `UserListView` / `UserDetailView` / `UserRoleUpdateView` (AdminRequiredMixin) - User & role management

### Convocatorias App
- Public: `PublicConvocatoriaListView`, `PublicConvocatoriaDetailView` (renders dynamic form + saves submission), `PublicConvocatoriaSuccessView`
- Admin (`AdminRequiredMixin`): Convocatoria CRUD, `ConvocatoriaFieldsView` (manage dynamic fields), submissions list/detail, `ConvocatoriaSubmissionExportView` (CSV)

### Capacitaciones App (on `aula-virtual` branch only)
- Public certificate verification, virtual classroom (dashboard, programa/clase detail, quizzes, certificates), admin CRUD for programs/modules/classes/participants/enrollments/quizzes/attendance/certificates. See the branch for details.

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

carnets/templates/carnets/
├── verificar.html                   # Public verification page
├── subir_foto.html                  # Photo upload form (handles token_used and token_expired states)
├── subir_foto_exito.html            # Upload success
├── mi_carne.html                    # Member's card view
├── dashboard/                       # Admin dashboard (Mobile Responsive)
│   ├── list.html                    # Card list with filters
│   ├── detail.html                  # Card detail view
│   ├── generar_carne.html           # Generate new card form
│   ├── estadisticas.html            # Card statistics
│   ├── suspender.html               # Suspend card form
│   └── renovar.html                 # Renew card form
└── emails/
    ├── solicitar_foto.html
    └── carne_listo.html

members/templates/members/           # Mobile Responsive
├── base_members.html                # Member portal base (hamburger menu, sidebar toggle)
├── login.html                       # Member login page
├── dashboard.html                   # Member home (with membership duration)
├── card.html                        # View my card (responsive card preview)
├── profile.html                     # My profile (with completion indicator)
├── profile_edit.html                # Edit profile form
├── password_change.html             # Change password form
└── password_change_done.html        # Password change success

dashboard/templates/dashboard/       # Mobile Responsive
├── base_dashboard.html              # Hamburger menu, sidebar toggle, overlay
├── login.html
├── home.html                        # Responsive KPI cards
├── application_list.html            # Hidden columns, compact badges, password status indicators
├── application_detail.html          # Stacked buttons, user account status section
├── password_set.html
├── password_set_done.html
├── directory/
│   ├── list.html                    # Simplified table for mobile
│   └── detail.html
├── featured_members/
│   ├── list.html                    # Hidden columns on mobile
│   ├── form.html
│   └── confirm_delete.html
└── emails/
    ├── compose.html
    ├── history.html                 # Compact email list
    └── detail.html
```

## Member Portal Sidebar Structure

```
MI PORTAL
├── Inicio (dashboard)
├── Mi Carnet (card)
└── Mi Perfil (profile)

CUENTA
├── Cambiar Contraseña (password_change)
└── Cerrar Sesión (logout)
```

## Dashboard Sidebar Structure

```
PRINCIPAL
├── Dashboard (dashboard_home)

GESTIÓN DE ASOCIADOS
├── Solicitudes (application_list)
├── Carnés Digitales (carnets:card_list)
├── Directorio Oficial (directory_list)
├── Convocatorias (convocatorias_admin:list)
└── Usuarios (user_list)

CONTENIDO WEB
├── Asociados Destacados (featured_member_list)
└── Noticias (news_list)

COMUNICACIONES
└── Correos (email_history)

ADMINISTRACIÓN
├── Pagos y Cartera (placeholder)
└── Configuración (placeholder)
```

> On the `aula-virtual` branch the sidebar also shows "Capacitaciones" and "Aula Virtual" links (not present on `main`).

## Custom Template Tags

### dashboard_extras (`dashboard/templatetags/dashboard_extras.py`)

| Filter | Usage | Purpose |
|--------|-------|---------|
| `get_item` | `{{ dict\|get_item:key }}` | Access dictionary items with variable keys |

**Usage Example:**
```django
{% load dashboard_extras %}
{% with status=password_status|get_item:app.pk %}
    {{ status.has_password }}
{% endwith %}
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
- Use `transaction.atomic()` with `select_for_update()` for concurrent operations
- Use Python's `logging` module for error tracking (logger per module)

### CSS Variables
```css
--asnc-navy: #1B2A41
--asnc-blue: #213a5c
--asnc-gold: #f4c343
--asnc-bg: #F5F7FA
--sidebar-width: 280px (desktop), 240px (tablet)
```

### Responsive Design (Mobile-First)
Both portals (member and admin) are fully responsive with the following breakpoints:

**Breakpoints:**
- Desktop: > 992px (full sidebar visible)
- Tablet: 768px - 992px (reduced sidebar width)
- Mobile: < 768px (hamburger menu, collapsible sidebar)
- Small phones: < 400px (compact padding)

**Mobile Features:**
- Fixed header with hamburger menu button
- Sidebar slides in from left with overlay
- Auto-close sidebar when clicking links
- Tables with hidden columns (d-none d-md-table-cell)
- Compact badges and buttons on small screens
- Stacked cards instead of horizontal layouts
- Simplified pagination (arrows instead of text)

**Member Profile Page Layout (`profile.html`):**
The profile page uses a two-column layout with flexbox for equal heights:
- **Left Column (col-lg-8)**: Main profile card with all user information
  - Header with avatar initials and profession badge
  - Profile completion alert (if < 100%)
  - Personal Information section
  - Professional Information section
  - Membership section (with duration)
  - Security section (dates)
  - Action buttons (Edit Profile, Change Password)
- **Right Column (col-lg-4)**: Two equal-height cards using `flex-grow-1`
  - **Profile Completion Card**: Gradient header, circular progress with gradient stroke, dynamic status badges (Completo/Casi listo/Buen avance/En progreso)
  - **Member Card Summary**: Mini card preview with status and expiry

**Responsive Templates:**
```
members/templates/members/
├── base_members.html        # Mobile header, sidebar toggle, overlay
├── dashboard.html           # 2-column grid on mobile
├── card.html                # Responsive card preview
└── profile.html             # Two-column layout with equal-height cards

dashboard/templates/dashboard/
├── base_dashboard.html      # Mobile header, sidebar toggle, overlay
├── home.html                # Responsive KPI cards
├── application_list.html    # Hidden columns, compact badges
├── application_detail.html  # Stacked decision buttons
├── directory/list.html      # Simplified table
├── emails/history.html      # Compact email list
└── featured_members/list.html # Hidden columns on mobile
```

## SEO Configuration

### Sitemap (`website/sitemaps.py`)
The sitemap includes the following pages with priorities:

| Page | Priority | Change Frequency |
|------|----------|------------------|
| home | 1.0 | weekly |
| application_create | 0.9 | weekly |
| about | 0.8 | weekly |
| events | 0.7 | weekly |

### Google Analytics
Google Analytics 4 is integrated via gtag.js in `base.html`:
- **Tracking ID**: G-1H2FNJ5PB8
- Loaded asynchronously in the `<head>` section

### Favicon
The favicon is configured in `config/urls.py` to redirect `/favicon.ico` to the S3 static URL using `settings.STATIC_URL`.

## Security Notes

- CSRF protection enabled on all forms
- CSRF_TRUSTED_ORIGINS configured for production HTTPS
- Custom error pages don't expose sensitive information
- Sensitive data in `.env` file (not committed)
- Protected views use Django's authentication mixins
- Photo upload uses unique UUID tokens (not user auth)
- Photo upload tokens expire after 72 hours
- robots.txt blocks admin, portal, and media paths
- Email recipients sent via BCC for privacy
- Password reset tokens with expiration

## Data Integrity & Race Condition Protection

The system uses atomic transactions and row-level locking to prevent race conditions:

### Card Number Generation (`carnets/models.py`)
```python
@classmethod
def generate_card_number(cls):
    with transaction.atomic():
        last_card = cls.objects.select_for_update().filter(
            card_number__startswith=prefix
        ).order_by('-card_number').first()
        # ... generates unique sequential number
```

### User Creation (`admissions/views.py`)
```python
def create_user_from_application(application):
    try:
        with transaction.atomic():
            user = User.objects.filter(email=application.email).first()
            if user:
                return user
            # ... create new user
    except IntegrityError:
        # Race condition: return existing user
        return User.objects.get(email=application.email)
```

### Application Approval (`admissions/views.py`)
```python
def change_application_status(request, pk, status):
    with transaction.atomic():
        application = MembershipApplication.objects.select_for_update().get(pk=pk)
        # ... create user and update status atomically
    # Email sent OUTSIDE transaction (won't rollback on email failure)
```

### Photo Upload (`carnets/views.py`)
```python
def form_valid(self, form):
    with transaction.atomic():
        card = MemberCard.objects.select_for_update().get(pk=self.card.pk)
        if card.photo_token_used:
            return render(...)  # Already used
        card.photo = form.cleaned_data['photo']
        card.photo_token_used = True
        card.status = MemberCard.Status.ACTIVE
        card.save()
```

### Cascade Delete Protection
- `MemberCard.user` uses `on_delete=models.PROTECT` to prevent accidental user deletion
- Attempting to delete a user with a card will raise `ProtectedError`

### Token Expiration
- Photo upload tokens expire after 72 hours (configurable via `PHOTO_TOKEN_EXPIRY_HOURS`)
- Expired tokens show a friendly message directing users to contact support

## Developer Branding (Vadom Data Consulting)

The platform includes developer credit for Vadom Data Consulting in the following locations:

| Location | Logo Type | File |
|----------|-----------|------|
| Public website footer | White logo | `templates/base.html` |
| Admin login page | Color logo | `dashboard/templates/dashboard/login.html` |
| Member login page | Color logo | `members/templates/members/login.html` |
| Card verification page (QR) | Color logo | `carnets/templates/carnets/verificar.html` |
| Member card PDF footer | Text credit | `carnets/utils.py` |
| All email templates | White logo (S3) | `templates/emails/`, `admissions/templates/admissions/emails/`, `carnets/templates/carnets/emails/` |

**Logo Files:**
- `static/images/vadom/vadom_logo.png` - Color logo for light backgrounds
- `static/images/vadom/vadom_logo_white.png` - White logo for dark backgrounds
- S3 URL: `https://vadomdata.s3.amazonaws.com/asnc/static/images/vadom/vadom_logo_white.png`

## Deployment Checklist

When deploying new changes (production lives at `/opt/asnc_web`):

```bash
# 1. Pull the latest code
cd /opt/asnc_web && git pull

# 2. Activate venv and install dependencies (DON'T skip this — missing deps cause
#    ModuleNotFoundError at runtime, e.g. xlsxwriter for the Excel export)
source venv/bin/activate
pip install -r requirements.txt

# 3. Apply migrations (commit migrations from dev — never run makemigrations in prod)
python manage.py migrate

# 4. Collect static files
python manage.py collectstatic --noinput

# 5. Restart server
sudo systemctl restart gunicorn  # or your server process
```

> Migrations are generated in development (`makemigrations`), committed to git, and only **applied** (`migrate`) in production.

## Future Enhancements (TODO)

- [x] ~~Member directory~~ (Implemented)
- [x] ~~Auto-create user account on approval~~ (Implemented)
- [x] ~~Digital member cards with QR~~ (Implemented)
- [x] ~~Role-based access control~~ (Implemented)
- [x] ~~Mobile responsive design~~ (Implemented - both portals)
- [ ] REST API endpoints
- [ ] Payment integration
- [ ] Two-factor authentication
- [ ] Celery for async email queue
- [ ] Migrate to Amazon SES for better deliverability
- [ ] Events management system (replace placeholder)
- [ ] Email open/click tracking
- [ ] Bulk email with rate limiting
- [x] ~~Card renewal workflow~~ (Implemented - CardRenewView)
- [x] ~~Member self-service profile editing~~ (Implemented - MemberProfileEditView)
- [x] ~~Password change for members~~ (Implemented - MemberPasswordChangeView)
- [x] ~~Membership duration display~~ (Implemented - years/months calculation)
- [x] ~~Unified approval email~~ (Welcome + password link in single email)
- [x] ~~Password status tracking~~ (Indicators in application list/detail)
- [x] ~~Resend password email~~ (Button in application detail for pending users)
- [x] ~~Google Analytics integration~~ (GA4 with gtag.js)
- [x] ~~SEO sitemap~~ (Includes home, about, events, application pages)
- [x] ~~Race condition protection~~ (Atomic transactions with select_for_update)
- [x] ~~Photo token expiration~~ (72-hour expiry for security)
- [x] ~~Cascade delete protection~~ (PROTECT on MemberCard.user)
- [x] ~~Developer branding~~ (Vadom Data Consulting credit in footer, emails, PDF)
