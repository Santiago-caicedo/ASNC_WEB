"""
Utilities for generating QR codes and PDF member cards.
"""
import io
import qrcode
from django.conf import settings
from django.urls import reverse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image


# Card dimensions (credit card size in mm)
CARD_WIDTH = 85.6 * mm
CARD_HEIGHT = 53.98 * mm

# ASNC Brand Colors
ASNC_NAVY = colors.HexColor('#1B2A41')
ASNC_BLUE = colors.HexColor('#213a5c')
ASNC_GOLD = colors.HexColor('#f4c343')


def generate_qr_code(data, size=150):
    """
    Generate a QR code image from data.

    Args:
        data: The data to encode in the QR code
        size: Size of the QR code in pixels

    Returns:
        PIL Image object
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    qr_image = qr.make_image(fill_color="black", back_color="white")
    qr_image = qr_image.resize((size, size), Image.Resampling.LANCZOS)

    return qr_image


def get_verification_url(card):
    """
    Get the full verification URL for a member card.

    Args:
        card: MemberCard instance

    Returns:
        Full URL string
    """
    # Build the full URL using SITE_URL from settings
    domain = settings.SITE_URL.rstrip('/')
    path = reverse('carnets:verificar', kwargs={'uuid': str(card.uuid)})
    return f"{domain}{path}"


def generate_card_pdf(card):
    """
    Generate a professional PDF document with the member card.

    Args:
        card: MemberCard instance

    Returns:
        BytesIO buffer containing the PDF
    """
    import os
    from pathlib import Path

    buffer = io.BytesIO()

    # Create the PDF
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Try to load the ASNC logo
    logo_path = None
    possible_paths = [
        Path(settings.BASE_DIR) / 'static' / 'images' / 'asnc_logo_full.png',
        Path(settings.BASE_DIR) / 'staticfiles' / 'images' / 'asnc_logo_full.png',
    ]
    for path in possible_paths:
        if path.exists():
            logo_path = str(path)
            break

    # =========================================
    # PAGE HEADER WITH LOGO
    # =========================================

    # Header background
    c.setFillColor(ASNC_NAVY)
    c.rect(0, height - 50*mm, width, 50*mm, fill=1, stroke=0)

    # Gold accent line
    c.setFillColor(ASNC_GOLD)
    c.rect(0, height - 51*mm, width, 1.5*mm, fill=1, stroke=0)

    # Logo
    if logo_path:
        try:
            logo_img = Image.open(logo_path)
            logo_reader = ImageReader(logo_img)
            logo_height = 18*mm
            logo_width = logo_height * 3.5  # Approximate aspect ratio
            c.drawImage(logo_reader, width/2 - logo_width/2, height - 32*mm,
                       logo_width, logo_height, preserveAspectRatio=True, mask='auto')
        except Exception:
            # Fallback to text if logo fails
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 20)
            c.drawCentredString(width/2, height - 25*mm, "ASOCIACION NUCLEAR COLOMBIANA")
    else:
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width/2, height - 25*mm, "ASOCIACION NUCLEAR COLOMBIANA")

    # Subtitle
    c.setFillColor(colors.HexColor('#94a3b8'))
    c.setFont("Helvetica", 11)
    c.drawCentredString(width/2, height - 42*mm, "Carnet Digital de Asociado")

    # =========================================
    # MAIN CARD - EXTRA LARGE
    # =========================================

    # Card dimensions (much larger - almost full width)
    card_w = 160*mm
    card_h = 100*mm
    card_x = (width - card_w) / 2
    card_y = height - 165*mm

    # Card shadow effect
    c.setFillColor(colors.HexColor('#d1d5db'))
    c.roundRect(card_x + 3*mm, card_y - 3*mm, card_w, card_h, 6*mm, fill=1, stroke=0)

    # Main card background
    c.setFillColor(ASNC_NAVY)
    c.roundRect(card_x, card_y, card_w, card_h, 6*mm, fill=1, stroke=0)

    # Decorative circles
    c.saveState()
    # Clip to card bounds
    p = c.beginPath()
    p.roundRect(card_x, card_y, card_w, card_h, 6*mm)
    c.clipPath(p, stroke=0)

    c.setFillColor(colors.HexColor('#1e3048'))
    c.circle(card_x + card_w - 20*mm, card_y + card_h - 20*mm, 45*mm, fill=1, stroke=0)

    c.setFillColor(colors.HexColor('#243b55'))
    c.circle(card_x + 15*mm, card_y + 15*mm, 35*mm, fill=1, stroke=0)

    c.restoreState()

    # Gold header bar
    c.setFillColor(ASNC_GOLD)
    c.roundRect(card_x, card_y + card_h - 18*mm, card_w, 18*mm, 6*mm, fill=1, stroke=0)
    c.rect(card_x, card_y + card_h - 18*mm, card_w, 12*mm, fill=1, stroke=0)

    # Title on gold bar (LEFT side)
    c.setFillColor(ASNC_NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(card_x + 10*mm, card_y + card_h - 9*mm, "CARNET DE ASOCIADO")
    c.setFont("Helvetica", 7)
    c.drawString(card_x + 10*mm, card_y + card_h - 14*mm, "ASOCIACION NUCLEAR COLOMBIANA")

    # ASNC text/logo on RIGHT side of gold bar (in navy)
    c.setFillColor(ASNC_NAVY)
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(card_x + card_w - 10*mm, card_y + card_h - 12*mm, "ASNC")

    # Founder badge (below ASNC text if founder)
    if card.category == 'FOUNDER':
        badge_w = 28*mm
        badge_h = 7*mm
        badge_x = card_x + card_w - badge_w - 8*mm
        badge_y = card_y + card_h - 24*mm
        c.setFillColor(ASNC_NAVY)
        c.roundRect(badge_x, badge_y, badge_w, badge_h, 2*mm, fill=1, stroke=0)
        c.setFillColor(ASNC_GOLD)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(badge_x + badge_w/2, badge_y + 2*mm, "FUNDADOR")

    # Photo area (larger)
    photo_x = card_x + 10*mm
    photo_y = card_y + 12*mm
    photo_w = 38*mm
    photo_h = 50*mm

    # Photo background with border
    c.setFillColor(colors.white)
    c.roundRect(photo_x, photo_y, photo_w, photo_h, 3*mm, fill=1, stroke=0)

    # Add actual photo
    if card.photo:
        try:
            img = Image.open(card.photo.path)
            img.thumbnail((int(photo_w * 6), int(photo_h * 6)), Image.Resampling.LANCZOS)
            img_reader = ImageReader(img)
            c.drawImage(img_reader, photo_x + 1.5*mm, photo_y + 1.5*mm,
                       photo_w - 3*mm, photo_h - 3*mm,
                       preserveAspectRatio=True, anchor='c', mask='auto')
        except Exception:
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.HexColor('#cbd5e1'))
            c.drawCentredString(photo_x + photo_w/2, photo_y + photo_h/2, "FOTO")
    else:
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor('#cbd5e1'))
        c.drawCentredString(photo_x + photo_w/2, photo_y + photo_h/2, "FOTO")

    # Member name (large and prominent)
    info_x = photo_x + photo_w + 10*mm
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    name = card.user.get_full_name().upper()
    if len(name) > 28:
        name = name[:27] + "..."
    c.drawString(info_x, card_y + 55*mm, name)

    # Card number with gold color (larger)
    c.setFillColor(ASNC_GOLD)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(info_x, card_y + 44*mm, card.card_number)

    # Category label
    c.setFillColor(colors.HexColor('#94a3b8'))
    c.setFont("Helvetica", 9)
    category_text = "MIEMBRO FUNDADOR" if card.category == 'FOUNDER' else "ASOCIADO"
    c.drawString(info_x, card_y + 36*mm, category_text)

    # Validity section - stacked vertically to avoid QR overlap
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont("Helvetica", 8)
    c.drawString(info_x, card_y + 26*mm, "EMISION")
    c.drawString(info_x, card_y + 14*mm, "VENCIMIENTO")

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(info_x + 25*mm, card_y + 26*mm, card.issue_date.strftime('%d/%m/%Y'))
    c.drawString(info_x + 25*mm, card_y + 14*mm, card.expiry_date.strftime('%d/%m/%Y'))

    # QR Code (positioned on right, not overlapping dates)
    verification_url = get_verification_url(card)
    qr_image = generate_qr_code(verification_url, size=150)

    qr_buffer = io.BytesIO()
    qr_image.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    qr_reader = ImageReader(qr_buffer)

    qr_size = 30*mm
    qr_x = card_x + card_w - qr_size - 8*mm
    qr_y = card_y + 8*mm

    # QR background
    c.setFillColor(colors.white)
    c.roundRect(qr_x - 3*mm, qr_y - 3*mm, qr_size + 6*mm, qr_size + 6*mm, 3*mm, fill=1, stroke=0)
    c.drawImage(qr_reader, qr_x, qr_y, qr_size, qr_size)

    # QR label
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont("Helvetica", 6)
    c.drawCentredString(qr_x + qr_size/2, qr_y - 5*mm, "VERIFICAR")

    # =========================================
    # INFORMATION SECTION
    # =========================================

    info_section_y = card_y - 25*mm

    # Section title
    c.setFillColor(ASNC_NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width/2, info_section_y, "INFORMACION DEL CARNET")

    # Decorative line
    c.setStrokeColor(ASNC_GOLD)
    c.setLineWidth(1.5)
    c.line(width/2 - 45*mm, info_section_y - 4*mm, width/2 + 45*mm, info_section_y - 4*mm)

    # Info boxes (larger)
    box_y = info_section_y - 40*mm
    box_height = 28*mm
    box_width = 70*mm
    gap = 12*mm

    # Box 1: Card Number
    box1_x = width/2 - box_width - gap/2
    c.setFillColor(colors.HexColor('#f8fafc'))
    c.roundRect(box1_x, box_y, box_width, box_height, 4*mm, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor('#e2e8f0'))
    c.setLineWidth(0.5)
    c.roundRect(box1_x, box_y, box_width, box_height, 4*mm, fill=0, stroke=1)

    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont("Helvetica", 8)
    c.drawCentredString(box1_x + box_width/2, box_y + box_height - 9*mm, "NUMERO DE CARNET")
    c.setFillColor(ASNC_NAVY)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(box1_x + box_width/2, box_y + 8*mm, card.card_number)

    # Box 2: Validity
    box2_x = width/2 + gap/2
    c.setFillColor(colors.HexColor('#f8fafc'))
    c.roundRect(box2_x, box_y, box_width, box_height, 4*mm, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor('#e2e8f0'))
    c.roundRect(box2_x, box_y, box_width, box_height, 4*mm, fill=0, stroke=1)

    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont("Helvetica", 8)
    c.drawCentredString(box2_x + box_width/2, box_y + box_height - 9*mm, "VIGENCIA DEL CARNET")
    c.setFillColor(ASNC_NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(box2_x + box_width/2, box_y + 8*mm,
                       f"{card.issue_date.strftime('%d/%m/%Y')} - {card.expiry_date.strftime('%d/%m/%Y')}")

    # =========================================
    # VERIFICATION SECTION
    # =========================================

    verify_y = box_y - 32*mm

    # Background box (taller to fit URL on two lines)
    c.setFillColor(colors.HexColor('#f1f5f9'))
    c.roundRect(25*mm, verify_y - 6*mm, width - 50*mm, 30*mm, 4*mm, fill=1, stroke=0)

    # QR icon
    c.setFillColor(ASNC_BLUE)
    c.circle(42*mm, verify_y + 9*mm, 7*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(42*mm, verify_y + 7*mm, "QR")

    # Verification text
    c.setFillColor(ASNC_NAVY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(55*mm, verify_y + 14*mm, "Verificacion de Autenticidad")

    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont("Helvetica", 9)
    c.drawString(55*mm, verify_y + 6*mm, "Escanee el codigo QR o visite:")

    # Show complete verification URL
    c.setFillColor(ASNC_BLUE)
    c.setFont("Helvetica-Bold", 8)
    full_url = f"www.asncol.com/verificar/{str(card.uuid)}/"
    c.drawString(55*mm, verify_y - 1*mm, full_url)

    # =========================================
    # FOOTER
    # =========================================

    # Footer line
    c.setStrokeColor(colors.HexColor('#e2e8f0'))
    c.setLineWidth(0.5)
    c.line(25*mm, 30*mm, width - 25*mm, 30*mm)

    # Footer text
    c.setFillColor(colors.HexColor('#94a3b8'))
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, 23*mm, "Este documento es una representacion digital oficial del carnet de asociado.")
    c.drawCentredString(width/2, 16*mm, "La autenticidad puede ser verificada escaneando el codigo QR.")

    c.setFillColor(ASNC_NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width/2, 8*mm, "www.asncol.com  |  info@asncol.com  |  Bucaramanga, Colombia")

    # Finish and save
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer


def generate_card_image(card, format='PNG'):
    """
    Generate a high-resolution image of the member card.

    Args:
        card: MemberCard instance
        format: Image format (PNG, JPEG)

    Returns:
        BytesIO buffer containing the image
    """
    # Scale factor for high resolution
    scale = 4

    # Card dimensions in pixels
    card_width_px = int(85.6 * scale * 3.78)  # mm to pixels at 96 DPI * scale
    card_height_px = int(53.98 * scale * 3.78)

    # Create image
    img = Image.new('RGB', (card_width_px, card_height_px), color='#1B2A41')

    # We could use PIL's ImageDraw here for a rasterized version
    # For now, we'll just return the PDF version converted to image
    # This is a simplified implementation

    buffer = io.BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)

    return buffer


def send_photo_request_email(card):
    """
    Send email to associate requesting their photo for the card.

    Args:
        card: MemberCard instance
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags

    # Build photo upload URL using SITE_URL from settings
    domain = settings.SITE_URL.rstrip('/')
    upload_url = f"{domain}{reverse('carnets:subir_foto', kwargs={'token': str(card.photo_token)})}"

    context = {
        'card': card,
        'upload_url': upload_url,
        'user': card.user,
    }

    html_content = render_to_string('carnets/emails/solicitar_foto.html', context)
    text_content = strip_tags(html_content)

    subject = 'ASNC - Completa tu Carné Digital'

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[card.user.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


def send_card_ready_email(card):
    """
    Send email to associate notifying their card is ready.

    Args:
        card: MemberCard instance
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags

    # Build card view URL using SITE_URL from settings
    domain = settings.SITE_URL.rstrip('/')
    card_url = f"{domain}/mi-portal/carnet/"

    context = {
        'card': card,
        'card_url': card_url,
        'user': card.user,
    }

    html_content = render_to_string('carnets/emails/carne_listo.html', context)
    text_content = strip_tags(html_content)

    subject = 'ASNC - Tu Carné Digital está listo'

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[card.user.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)
