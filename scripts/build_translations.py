"""
Genera los catálogos de traducción EN del sitio público (locale/en/LC_MESSAGES/).

Fuente única de las traducciones ES -> EN. Las claves (msgid) DEBEN coincidir
EXACTAMENTE con el texto dentro de los {% trans "..." %} / {% blocktrans %}
de las plantillas. El idioma por defecto es español (msgid = español); aquí solo
se definen las cadenas en inglés (msgstr).

Uso:
    python scripts/build_translations.py

Requiere: polib (pip install polib). Genera .po y .mo (Django lee el .mo en
runtime con la librería estándar gettext de Python; NO requiere gettext del SO).
"""
import os

import polib

# ---------------------------------------------------------------------------
# Traducciones ES -> EN, agrupadas por plantilla.
# ---------------------------------------------------------------------------
TRANSLATIONS = {}

# --- templates/base.html (header + footer, compartido por todo el sitio) ---
TRANSLATIONS.update({
    "Síguenos:": "Follow us:",
    "Miembro Institucional": "Institutional Member",
    "Inicio": "Home",
    "Quiénes Somos": "About Us",
    "Eventos": "Events",
    "Noticias": "News",
    "Acceso Asociados": "Member Login",
    "¡Únete a la ASNC!": "Join the ASNC!",
    "Promoviendo el desarrollo pacífico, seguro y sostenible de la ciencia y tecnología nuclear en Colombia.":
        "Promoting the peaceful, safe and sustainable development of nuclear science and technology in Colombia.",
    "Navegación": "Navigation",
    "Sobre Nosotros": "About Us",
    "Afiliarse": "Join",
    "Legal": "Legal",
    "Estatutos": "Bylaws",
    "Política de Datos": "Data Policy",
    "Contacto": "Contact",
    "Todos los derechos reservados.": "All rights reserved.",
    "Desarrollado por": "Developed by",
})


def build():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(base_dir, 'locale', 'en', 'LC_MESSAGES')
    os.makedirs(out_dir, exist_ok=True)

    po = polib.POFile()
    po.metadata = {
        'Project-Id-Version': 'ASNC 1.0',
        'Report-Msgid-Bugs-To': 'info@asncol.com',
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Transfer-Encoding': '8bit',
        'Language': 'en',
    }

    for msgid, msgstr in TRANSLATIONS.items():
        po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))

    po_path = os.path.join(out_dir, 'django.po')
    mo_path = os.path.join(out_dir, 'django.mo')
    po.save(po_path)
    po.save_as_mofile(mo_path)
    print(f'OK: {len(TRANSLATIONS)} cadenas -> {po_path} y {mo_path}')


if __name__ == '__main__':
    build()
