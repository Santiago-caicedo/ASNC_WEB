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
- **Images**: Pillow (for ImageField support)
- **SEO**: django.contrib.sitemaps
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
│   └── templates/dashboard/     # Dashboard templates
│       └── featured_members/    # CRUD templates for featured members
├── website/                     # Public-facing pages
│   ├── templates/website/       # Home, About, Events pages
│   ├── models.py                # FeaturedMember model
│   ├── views.py                 # HomeView, AboutView, EventsView
│   └── sitemaps.py              # SEO sitemaps
├── templates/                   # Base templates
│   ├── base.html                # Main layout with SEO meta tags
│   ├── robots.txt               # SEO robots file
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
| `dashboard` | Protected admin views, KPIs, application management, featured members CRUD |
| `website` | Public pages: homepage, about, events |

## Key Models

### User (`users/models.py`)
- Extends `AbstractUser`
- `email` is the primary authentication field (unique)
- Standard Django auth fields

### MembershipApplication (`admissions/models.py`)
- `uuid`: Unique identifier for tracking
- `first_name`, `last_name`, `email`, `phone`
- `profession`, `current_job`, `institution`, `linkedin_url`
- `contribution_statement`: TextField for applicant's motivation
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

### FeaturedMember (`website/models.py`)
- `full_name`: CharField (200)
- `photo`: ImageField (upload to `featured_members/`)
- `association_position`: CharField - Role in ASNC
- `profession`: CharField
- `professional_trajectory`: TextField
- `linkedin_url`: URLField (optional)
- `is_active`: BooleanField (default True)
- `display_order`: PositiveIntegerField (for sorting)

## URL Structure

```
# Public Website
/                              → Homepage (HomeView)
/quienes-somos/                → About page with team (AboutView)
/eventos/                      → Events page - under construction (EventsView)
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
/portal/asociados-destacados/          → List featured members
/portal/asociados-destacados/crear/    → Create new member
/portal/asociados-destacados/<id>/editar/   → Edit member
/portal/asociados-destacados/<id>/eliminar/ → Delete member

# Admin
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
- Favicon: `static/images/icon_asnc.png`
- Use `{% static 'path' %}` template tag
- Media uploads go to `media/` directory

### Frontend Assets (CDN)
- Bootstrap 5.3.0 (CSS + JS)
- Bootstrap Icons
- Google Fonts: Outfit
- anime.js - Used for scroll animations on homepage

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

### Sitemap (`/sitemap.xml`)
- Auto-generated via `django.contrib.sitemaps`
- Includes: home, about, events
- Configured in `website/sitemaps.py`

### robots.txt (`/robots.txt`)
- Allows all public pages
- Blocks: `/admin/`, `/portal/`, `/media/applications/`
- References sitemap URL

### SEO Blocks Available in Templates
```django
{% block meta_description %}Custom description{% endblock %}
{% block meta_keywords %}custom, keywords{% endblock %}
{% block og_title %}Custom OG Title{% endblock %}
{% block og_description %}Custom OG description{% endblock %}
{% block og_image %}https://...{% endblock %}
{% block twitter_title %}...{% endblock %}
{% block twitter_description %}...{% endblock %}
{% block extra_structured_data %}...{% endblock %}
```

## Custom Error Pages

All error pages have consistent ASNC branding:

| File | Error | Description |
|------|-------|-------------|
| `400.html` | Bad Request | Purple accent, question icon |
| `403.html` | Forbidden | Red accent, shield icon |
| `403_csrf.html` | CSRF Failed | Red accent, tips for resolution |
| `404.html` | Not Found | Gold accent, search icon |
| `500.html` | Server Error | Orange accent, warning icon |

Features:
- Animated atom decorations
- ASNC logo header
- Action buttons (Home, Back, Reload)
- Fully responsive
- No sensitive information exposed

## Navigation

### Active Page Highlighting
The navbar automatically highlights the current page in gold color using:
```django
{% if request.resolver_match.url_name == 'page_name' %}active{% endif %}
```

### Navbar Links
- Inicio → `/` (home)
- Quiénes Somos → `/quienes-somos/` (about)
- Eventos → `/eventos/` (events)
- Acceso Asociados → `/portal/login/`
- ¡Únete a la ASNC! → `/solicitud/`

## Public Pages

### Homepage (`website/home.html`)
- Hero section with CTA
- Nuclenergy section (divulgation content types)
- NuclenergyData section (digital tool preview)
- Benefits section (why join ASNC)
- Fission animation with anime.js

### About Page (`website/about.html`)
- Hero with background image
- Mission section (Misión, Visión 2030, Valores)
- Organizational structure (Junta Directiva, 3 Comités)
- Team section with FeaturedMember cards
- Modal for member details
- CTA to join

### Events Page (`website/events.html`)
- Hero section
- "Under Construction" card with atom animation
- Coming features preview
- Event types: Conferencias, Webinars, Talleres, Networking
- CTA to join for notifications

## Dashboard Features

### Featured Members Management
CRUD interface under "Contenido Web" menu:
- List view with photo thumbnails
- Create/Edit form with image upload
- Delete confirmation
- Drag-order support via `display_order`

### Dashboard Sidebar Structure
```
PRINCIPAL
├── Inicio (dashboard_home)
└── Solicitudes (application_list)

CONTENIDO WEB
└── Asociados Destacados (featured_member_list)

GESTIÓN ACADÉMICA
├── Eventos (placeholder)
├── Publicaciones (placeholder)
└── Congresos (placeholder)

ADMINISTRACIÓN
├── Reportes (placeholder)
├── Usuarios (placeholder)
└── Configuración (placeholder)
```

## Views Summary

### Website App
- `HomeView` (TemplateView) - Public homepage
- `AboutView` (ListView) - About page with FeaturedMembers
- `EventsView` (TemplateView) - Events page (under construction)

### Admissions App
- `ApplicationCreateView` (CreateView) - Membership form
- `ApplicationSuccessView` (TemplateView) - Confirmation
- `ApplicationListView` (LoginRequiredMixin, ListView)
- `ApplicationDetailView` (LoginRequiredMixin, DetailView)
- `change_application_status()` - Status change function

### Dashboard App
- `CustomLoginView` (LoginView) - Email-based login
- `DashboardHomeView` (LoginRequiredMixin, TemplateView) - KPIs
- `FeaturedMemberListView` - List featured members
- `FeaturedMemberCreateView` - Create new member
- `FeaturedMemberUpdateView` - Edit member
- `FeaturedMemberDeleteView` - Delete confirmation

## Authentication Flow

- Login URL: `/portal/login/`
- Logout URL: `/portal/logout/`
- Uses email (not username) for authentication
- Protected views redirect to login if not authenticated
- After login, redirects to `/portal/`
- After logout, redirects to `/portal/login/`

## Storage Configuration

### Development (DEBUG=True)
- Static files: `/static/` served locally
- Media files: `/media/` served locally

### Production (DEBUG=False)
- Uses AWS S3 via django-storages
- Bucket: `vadomdata`
- Region: `us-east-1`
- Static: `{S3_CLIENT_PREFIX}/static/`
- Media: `{S3_CLIENT_PREFIX}/media/`
- Featured member photos: `{S3_CLIENT_PREFIX}/media/featured_members/`

## Security Notes

- CSRF protection enabled on all forms
- CSRF_TRUSTED_ORIGINS configured for production HTTPS
- Custom error pages don't expose sensitive information
- Sensitive data in `.env` file (not committed)
- Protected views use Django's authentication mixins
- robots.txt blocks admin and portal paths

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

## SEO Checklist (Manual Steps)

- [ ] Create `og-image.png` (1200x630px) in `static/images/`
- [ ] Register site in Google Search Console
- [ ] Verify domain ownership (DNS TXT record)
- [ ] Submit sitemap: `https://www.asncol.com/sitemap.xml`
- [ ] Update social media links in base.html with real ASNC accounts
- [ ] (Optional) Register in Google My Business

## Future Enhancements (TODO)

- [ ] REST API endpoints
- [ ] Member directory
- [ ] Payment integration
- [ ] Auto-create user account on approval
- [ ] Role-based access control
- [ ] Two-factor authentication
- [ ] Celery for async email queue
- [ ] Configure SMTP for production emails
- [ ] Pagination on application list
- [ ] Events management system (replace placeholder)
- [ ] Search/filter functionality on dashboard
