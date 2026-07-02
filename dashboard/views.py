import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView, FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.utils import formataddr
from admissions.models import MembershipApplication
from website.models import FeaturedMember, NewsArticle
from carnets.models import MemberCard
from users.models import User
from .forms import FeaturedMemberForm, NewsArticleForm, EmailComposeForm, UserRoleForm
from .models import SentEmail


# ============================================
# Access Control Mixins
# ============================================

class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin to restrict views to any staff user (admins only)."""
    login_url = '/acceso/'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('/mi-portal/')
        return super().handle_no_permission()


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to restrict views to full administrators only."""
    login_url = '/acceso/'

    def test_func(self):
        user = self.request.user
        return user.is_superuser or (user.is_staff and user.is_admin)

    def handle_no_permission(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff and user.can_edit_news:
                messages.warning(self.request, 'No tienes permisos para acceder a esa sección.')
                return redirect('news_list')
            return redirect('/mi-portal/')
        return super().handle_no_permission()


class NewsEditorRequiredMixin(UserPassesTestMixin):
    """Mixin to restrict views to users who can edit news or are admins."""
    login_url = '/acceso/'

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.can_edit_news or user.is_admin)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('/mi-portal/')
        return super().handle_no_permission()


# ============================================
# Authentication
# ============================================

class CustomLoginView(LoginView):
    template_name = 'dashboard/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_admin:
            return '/portal/'
        if user.is_staff and user.can_edit_news:
            return '/portal/noticias/'
        return '/mi-portal/'


# ============================================
# Dashboard Home
# ============================================

class DashboardHomeView(AdminRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Full admin KPIs
        context['pending_count'] = MembershipApplication.objects.filter(status='PENDING').count()
        context['review_count'] = MembershipApplication.objects.filter(status='REVIEW').count()
        context['members_count'] = FeaturedMember.objects.filter(is_active=True).count()
        context['active_cards'] = MemberCard.objects.filter(status=MemberCard.Status.ACTIVE).count()
        context['pending_photo_cards'] = MemberCard.objects.filter(status=MemberCard.Status.PENDING_PHOTO).count()
        context['total_associates'] = MemberCard.objects.count()
        context['founders_count'] = MemberCard.objects.filter(category=MemberCard.Category.FOUNDER).count()
        context['news_count'] = NewsArticle.objects.count()
        context['published_count'] = NewsArticle.objects.filter(is_published=True).count()
        return context


# ============================================
# CRUD para Asociados Destacados (Admin only)
# ============================================

class FeaturedMemberListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    """Lista de asociados destacados"""
    model = FeaturedMember
    template_name = 'dashboard/featured_members/list.html'
    context_object_name = 'members'
    ordering = ['display_order', 'full_name']


class FeaturedMemberCreateView(AdminRequiredMixin, LoginRequiredMixin, CreateView):
    """Crear nuevo asociado destacado"""
    model = FeaturedMember
    form_class = FeaturedMemberForm
    template_name = 'dashboard/featured_members/form.html'
    success_url = reverse_lazy('featured_member_list')

    def form_valid(self, form):
        messages.success(self.request, 'Asociado destacado creado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Agregar Asociado Destacado'
        context['button_text'] = 'Crear Asociado'
        return context


class FeaturedMemberUpdateView(AdminRequiredMixin, LoginRequiredMixin, UpdateView):
    """Editar asociado destacado"""
    model = FeaturedMember
    form_class = FeaturedMemberForm
    template_name = 'dashboard/featured_members/form.html'
    success_url = reverse_lazy('featured_member_list')

    def form_valid(self, form):
        messages.success(self.request, 'Asociado destacado actualizado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Asociado Destacado'
        context['button_text'] = 'Guardar Cambios'
        return context


class FeaturedMemberDeleteView(AdminRequiredMixin, LoginRequiredMixin, DeleteView):
    """Eliminar asociado destacado"""
    model = FeaturedMember
    template_name = 'dashboard/featured_members/confirm_delete.html'
    success_url = reverse_lazy('featured_member_list')

    def form_valid(self, form):
        messages.success(self.request, 'Asociado destacado eliminado exitosamente.')
        return super().form_valid(form)


# ============================================
# CRUD para Noticias (Staff - includes news editors)
# ============================================

class NewsListView(NewsEditorRequiredMixin, LoginRequiredMixin, ListView):
    """Lista de noticias"""
    model = NewsArticle
    template_name = 'dashboard/news/list.html'
    context_object_name = 'articles'
    ordering = ['-created_at']
    paginate_by = 20


class NewsCreateView(NewsEditorRequiredMixin, LoginRequiredMixin, CreateView):
    """Crear nueva noticia"""
    model = NewsArticle
    form_class = NewsArticleForm
    template_name = 'dashboard/news/form.html'
    success_url = reverse_lazy('news_list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, 'Noticia creada exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nueva Noticia'
        context['button_text'] = 'Crear Noticia'
        return context


class NewsUpdateView(NewsEditorRequiredMixin, LoginRequiredMixin, UpdateView):
    """Editar noticia"""
    model = NewsArticle
    form_class = NewsArticleForm
    template_name = 'dashboard/news/form.html'
    success_url = reverse_lazy('news_list')

    def form_valid(self, form):
        messages.success(self.request, 'Noticia actualizada exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Noticia'
        context['button_text'] = 'Guardar Cambios'
        return context


class NewsDeleteView(NewsEditorRequiredMixin, LoginRequiredMixin, DeleteView):
    """Eliminar noticia"""
    model = NewsArticle
    template_name = 'dashboard/news/confirm_delete.html'
    success_url = reverse_lazy('news_list')

    def form_valid(self, form):
        messages.success(self.request, 'Noticia eliminada exitosamente.')
        return super().form_valid(form)


# Imágenes permitidas dentro del contenido de las noticias (editor Quill)
NEWS_IMAGE_ALLOWED_TYPES = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif',
    'image/webp': 'webp',
}
NEWS_IMAGE_MAX_SIZE = 5 * 1024 * 1024  # 5 MB por imagen


@login_required
@require_POST
def news_image_upload(request):
    """Recibe una imagen del editor Quill, la guarda en el almacenamiento
    (S3 en producción, local en desarrollo) y devuelve su URL pública.

    Así el contenido de la noticia guarda solo la URL de la imagen, en vez
    de incrustarla como base64 (que hacía crecer el POST más allá de
    DATA_UPLOAD_MAX_MEMORY_SIZE)."""
    user = request.user
    if not (user.can_edit_news or user.is_admin):
        return JsonResponse({'error': 'No tienes permisos para subir imágenes.'}, status=403)

    upload = request.FILES.get('image')
    if not upload:
        return JsonResponse({'error': 'No se recibió ninguna imagen.'}, status=400)

    extension = NEWS_IMAGE_ALLOWED_TYPES.get(upload.content_type)
    if not extension:
        return JsonResponse(
            {'error': 'Formato no permitido. Usa JPG, PNG, GIF o WEBP.'}, status=400
        )

    if upload.size > NEWS_IMAGE_MAX_SIZE:
        return JsonResponse(
            {'error': 'La imagen supera el tamaño máximo de 5 MB.'}, status=400
        )

    filename = f'news/content/{uuid.uuid4().hex}.{extension}'
    saved_name = default_storage.save(filename, upload)
    return JsonResponse({'url': default_storage.url(saved_name)})


# ============================================
# Módulo de Correos / Mailing (Admin only)
# ============================================

class EmailComposeView(AdminRequiredMixin, LoginRequiredMixin, FormView):
    """Vista para componer y enviar correos"""
    template_name = 'dashboard/emails/compose.html'
    form_class = EmailComposeForm
    success_url = reverse_lazy('email_history')

    def form_valid(self, form):
        recipients = form.get_recipients()
        subject = form.cleaned_data['subject']
        message_content = form.cleaned_data['message']

        context = {
            'subject': subject,
            'message': message_content,
        }

        html_content = render_to_string('emails/base_email.html', context)
        text_content = f"{subject}\n\n{message_content}\n\n--\nAsociación Nuclear Colombiana\ninfo@asncol.com"

        success = True
        error_msg = ''

        try:
            from_email = formataddr(('Asociación Nuclear Colombiana', settings.DEFAULT_FROM_EMAIL))
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[settings.DEFAULT_FROM_EMAIL],
                bcc=recipients
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)

        except Exception as e:
            success = False
            error_msg = str(e)

        SentEmail.objects.create(
            subject=subject,
            message=message_content,
            recipients=', '.join(recipients),
            recipients_count=len(recipients),
            sent_by=self.request.user,
            success=success,
            error_message=error_msg
        )

        if success:
            messages.success(self.request, f'Correo enviado exitosamente a {len(recipients)} destinatario(s).')
        else:
            messages.error(self.request, f'Error al enviar el correo: {error_msg}')

        return super().form_valid(form)


class EmailHistoryView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    """Lista de correos enviados"""
    model = SentEmail
    template_name = 'dashboard/emails/history.html'
    context_object_name = 'emails'
    ordering = ['-sent_at']
    paginate_by = 20


class EmailDetailView(AdminRequiredMixin, LoginRequiredMixin, DetailView):
    """Detalle de un correo enviado"""
    model = SentEmail
    template_name = 'dashboard/emails/detail.html'
    context_object_name = 'email'


# ============================================
# Gestión de Usuarios (Admin only)
# ============================================

class UserListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    """Lista de todos los usuarios del sistema."""
    model = User
    template_name = 'dashboard/users/list.html'
    context_object_name = 'users_list'
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')

        # Filter by role
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role=role)

        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        # Search
        search = self.request.GET.get('q')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['role_choices'] = User.Role.choices
        context['current_role'] = self.request.GET.get('role', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['total_users'] = User.objects.count()
        context['staff_count'] = User.objects.filter(is_staff=True).count()
        context['editors_count'] = User.objects.filter(can_edit_news=True).count()
        return context


class UserDetailView(AdminRequiredMixin, LoginRequiredMixin, DetailView):
    """Detalle de un usuario."""
    model = User
    template_name = 'dashboard/users/detail.html'
    context_object_name = 'user_detail'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.object
        # Check if user has a member card
        try:
            context['member_card'] = user_obj.member_card
        except Exception:
            context['member_card'] = None
        return context


class UserRoleUpdateView(AdminRequiredMixin, LoginRequiredMixin, UpdateView):
    """Editar rol de un usuario."""
    model = User
    form_class = UserRoleForm
    template_name = 'dashboard/users/role_form.html'
    context_object_name = 'user_detail'

    def get_success_url(self):
        return reverse_lazy('user_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        user_obj = form.save(commit=False)

        # If role is ADMIN, ensure is_staff is True
        if user_obj.role == User.Role.ADMIN:
            user_obj.is_staff = True

        user_obj.save()
        messages.success(self.request, f'Rol de {user_obj.get_full_name() or user_obj.email} actualizado exitosamente.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Rol - {self.object.get_full_name() or self.object.email}'
        return context


# ============================================
# Directorio Oficial de Asociados (Admin only)
# ============================================

class DirectoryListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    """Lista del directorio oficial de asociados vinculados."""
    model = MemberCard
    template_name = 'dashboard/directory/list.html'
    context_object_name = 'members'
    paginate_by = 20

    def get_queryset(self):
        queryset = MemberCard.objects.select_related(
            'user', 'application', 'issued_by'
        ).order_by('-created_at')

        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        search = self.request.GET.get('q')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(card_number__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(application__profession__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category_choices'] = MemberCard.Category.choices
        context['status_choices'] = MemberCard.Status.choices
        context['current_category'] = self.request.GET.get('category', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')

        context['total_members'] = MemberCard.objects.count()
        context['active_members'] = MemberCard.objects.filter(status=MemberCard.Status.ACTIVE).count()
        context['founders_count'] = MemberCard.objects.filter(category=MemberCard.Category.FOUNDER).count()

        return context


class DirectoryDetailView(AdminRequiredMixin, LoginRequiredMixin, DetailView):
    """Expediente detallado de un asociado."""
    model = MemberCard
    template_name = 'dashboard/directory/detail.html'
    context_object_name = 'member'

    def get_queryset(self):
        return MemberCard.objects.select_related(
            'user', 'application', 'issued_by'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verifications'] = self.object.verifications.all()[:10]
        from members.views import build_qr_data_uri
        context['qr_data_uri'] = build_qr_data_uri(self.object)
        return context
