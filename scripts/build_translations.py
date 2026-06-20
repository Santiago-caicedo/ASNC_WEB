"""
Genera el catálogo de traducción EN del sitio público (locale/en/LC_MESSAGES/).

Estrategia robusta (sin requerir gettext del SO):
  1. Extrae los msgid EXACTOS de las plantillas públicas usando la propia
     maquinaria de Django (`templatize`), igual que hace `makemessages`.
  2. Empareja cada msgid con su traducción al inglés del diccionario de abajo,
     comparando por TEXTO NORMALIZADO (colapsando espacios/saltos de línea), de
     modo que el espaciado interno de los {% blocktrans %} no cause desajustes.
  3. Compila a .po y .mo con polib (Django lee el .mo en runtime con la
     librería estándar de Python; NO necesita gettext instalado).

Uso:
    python scripts/build_translations.py

Si agregas/quitas {% trans %} en las plantillas, actualiza TRANSLATIONS y
vuelve a ejecutar. Reporta al final cualquier cadena sin traducir.
"""
import ast
import os
import re
import sys

import polib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # carpeta scripts/

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django  # noqa: E402
django.setup()
from django.utils.translation.template import templatize  # noqa: E402

# Plantillas públicas internacionalizadas.
TEMPLATE_FILES = [
    'templates/base.html',
    'website/templates/website/home.html',
    'website/templates/website/about.html',
    'website/templates/website/events.html',
    'website/templates/website/privacy_policy.html',
    'website/templates/website/news/list.html',
    'website/templates/website/news/detail.html',
    'admissions/templates/admissions/application_form.html',
    'admissions/templates/admissions/application_success.html',
    'convocatorias/templates/convocatorias/public/list.html',
    'convocatorias/templates/convocatorias/public/detail.html',
    'convocatorias/templates/convocatorias/public/success.html',
    'carnets/templates/carnets/verificar.html',
]

# ---------------------------------------------------------------------------
# Traducciones ES -> EN. Las claves se comparan por texto normalizado, así que
# pueden escribirse en una sola línea aunque en la plantilla sean multilínea.
# ---------------------------------------------------------------------------
TRANSLATIONS = {}

# --- base.html (header + footer) ---
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

# --- home.html ---
TRANSLATIONS.update({
    "El Futuro de Colombia": "The Future of Colombia",
    "es Nuclear": "is Nuclear",
    "Somos una comunidad científica que impulsa el desarrollo de la energía nuclear como pilar fundamental de la transición energética justa en Colombia.":
        "We are a scientific community driving the development of nuclear energy as a fundamental pillar of a just energy transition in Colombia.",
    "Únete a la ASNC": "Join the ASNC",
    "Descubre más": "Discover more",
    "Noticias de la Asociación": "Association News",
    "Próximamente publicaremos novedades.": "We will publish updates soon.",
    "Ver todas las noticias": "View all news",
    "Scroll": "Scroll",
    "Actualidad Nuclear": "Nuclear News",
    "Noticias del Sector": "Industry News",
    "Lo más relevante del mundo nuclear: avances, investigaciones y tendencias.":
        "The most relevant from the nuclear world: advances, research and trends.",
    "Nuclear": "Nuclear",
    "Próximamente publicaremos noticias del sector nuclear.": "We will publish nuclear industry news soon.",
    "El Poder del Átomo": "The Power of the Atom",
    "Fisión Nuclear:": "Nuclear Fission:",
    "Energía del Futuro": "Energy of the Future",
    "La fisión nuclear ocurre cuando un neutrón impacta un núcleo de uranio-235, dividiéndolo en dos fragmentos y liberando una cantidad inmensa de energía, junto con más neutrones que continúan la reacción en cadena.":
        "Nuclear fission occurs when a neutron strikes a uranium-235 nucleus, splitting it into two fragments and releasing an immense amount of energy, along with more neutrons that sustain the chain reaction.",
    "Impacto del Neutrón": "Neutron Impact",
    "Un neutrón colisiona con el núcleo de U-235": "A neutron collides with the U-235 nucleus",
    "División del Núcleo": "Nucleus Splitting",
    "El átomo se vuelve inestable y se divide": "The atom becomes unstable and splits",
    "Liberación de Energía": "Energy Release",
    "Se libera energía térmica y más neutrones": "Thermal energy and more neutrons are released",
    "Reacción en Cadena": "Chain Reaction",
    "Los neutrones continúan el proceso": "The neutrons continue the process",
    "REACCIÓN EN CADENA INICIADA": "CHAIN REACTION INITIATED",
    "Energía Liberada": "Energy Released",
    "Aplicaciones": "Applications",
    "La Tecnología Nuclear Transforma Vidas": "Nuclear Technology Transforms Lives",
    "Más allá de la generación eléctrica, la energía nuclear tiene aplicaciones fundamentales en medicina, agricultura e industria.":
        "Beyond electricity generation, nuclear energy has essential applications in medicine, agriculture and industry.",
    "Medicina Nuclear": "Nuclear Medicine",
    "Diagnóstico por imágenes, tratamiento del cáncer con radioterapia, y esterilización de equipos médicos.":
        "Diagnostic imaging, cancer treatment with radiotherapy, and sterilization of medical equipment.",
    "PET y SPECT scan": "PET and SPECT scan",
    "Radioterapia oncológica": "Oncological radiotherapy",
    "Radioisótopos terapéuticos": "Therapeutic radioisotopes",
    "Agricultura Nuclear": "Nuclear Agriculture",
    "Agricultura": "Agriculture",
    "Mejora genética de cultivos, control de plagas y conservación de alimentos mediante radiación.":
        "Genetic crop improvement, pest control and food preservation through radiation.",
    "Mutaciones benéficas": "Beneficial mutations",
    "Esterilización de insectos": "Insect sterilization",
    "Irradiación de alimentos": "Food irradiation",
    "Energía Nuclear": "Nuclear Energy",
    "Energía Limpia": "Clean Energy",
    "Generación eléctrica continua, cero emisiones de CO2 y alta densidad energética.":
        "Continuous electricity generation, zero CO2 emissions and high energy density.",
    "24/7 sin intermitencia": "24/7 with no intermittency",
    "Huella de carbono mínima": "Minimal carbon footprint",
    "Máxima eficiencia": "Maximum efficiency",
    "SuperNuc - Guardián de la Energía Nuclear": "SuperNuc - Guardian of Nuclear Energy",
    "Ciencia Real": "Real Science",
    "Alcance Global": "Global Reach",
    "Plataforma Oficial de Divulgación ASNC": "Official ASNC Outreach Platform",
    "Donde la": "Where",
    "Ciencia": "Science",
    "Vence a los": "Defeats",
    "Mitos": "Myths",
    "La voz oficial de la Asociación Nuclear Colombiana en el mundo digital. Educamos, informamos y derribamos mitos sobre la energía nuclear con contenido verificado por expertos.":
        "The official voice of the Colombian Nuclear Association in the digital world. We educate, inform and debunk myths about nuclear energy with expert-verified content.",
    "Podcast": "Podcast",
    "Cursos": "Courses",
    "Artículos": "Articles",
    "Videos": "Videos",
    "Explorar Nuclenergy": "Explore Nuclenergy",
    "Contenido verificado": "Verified content",
    "Respaldado por la ASNC": "Backed by the ASNC",
    "Herramienta Digital": "Digital Tool",
    "Atlas Mundial de": "World Atlas of",
    "Reactores Nucleares": "Nuclear Reactors",
    "Descubre NuclenergyData, nuestra plataforma interactiva que te permite explorar el estado de la energía nuclear a nivel global. Visualiza la ubicación de cada reactor, compara estadísticas entre países y accede a información actualizada del sector.":
        "Discover NuclenergyData, our interactive platform that lets you explore the state of nuclear energy worldwide. View the location of each reactor, compare statistics across countries and access up-to-date industry information.",
    "Atlas Mundial": "World Atlas",
    "Visualiza reactores por país en un mapa interactivo": "View reactors by country on an interactive map",
    "Comparador": "Comparator",
    "Compara estadísticas entre diferentes naciones": "Compare statistics across different nations",
    "Datos Actualizados": "Up-to-Date Data",
    "Información actualizada de reactores operativos": "Up-to-date information on operating reactors",
    "Explorar NuclenergyData": "Explore NuclenergyData",
    "Reactores Activos": "Active Reactors",
    "Países con Nuclear": "Countries with Nuclear Power",
    "En Construcción": "Under Construction",
    "Membresía ASNC": "ASNC Membership",
    "¿Por qué ser parte de la ASNC?": "Why be part of the ASNC?",
    "Más que una asociación, somos un ecosistema de crecimiento profesional diseñado para potenciar tu carrera en el sector nuclear.":
        "More than an association, we are a professional growth ecosystem designed to boost your career in the nuclear sector.",
    "Comunidad Científica Colombiana": "Colombian Scientific Community",
    "Únete a la red de profesionales, investigadores y estudiantes del sector nuclear más grande de Colombia. Conecta con expertos y construye relaciones valiosas.":
        "Join the largest network of nuclear sector professionals, researchers and students in Colombia. Connect with experts and build valuable relationships.",
    "Lo más solicitado": "Most requested",
    "Eventos Exclusivos": "Exclusive Events",
    "Acceso preferencial a congresos, seminarios, conferencias y encuentros del sector nuclear.":
        "Preferential access to congresses, seminars, conferences and gatherings of the nuclear sector.",
    "Material Exclusivo": "Exclusive Material",
    "Acceso a contenido especializado, estudios, publicaciones y recursos educativos del sector.":
        "Access to specialized content, studies, publications and educational resources of the sector.",
    "Formación y Capacitación": "Training and Education",
    "Cursos, talleres y oportunidades de formación con instituciones nacionales e internacionales.":
        "Courses, workshops and training opportunities with national and international institutions.",
    "Conexión con la Industria": "Industry Connection",
    "Vínculos directos con empresas, instituciones y organizaciones a nivel nacional e internacional.":
        "Direct links with companies, institutions and organizations at the national and international level.",
    "Nuestros Principios": "Our Principles",
    "Respeto e Integridad": "Respect and Integrity",
    "La ASNC promulga y defiende el respeto entre las personas, manteniendo su integridad y dignidad sin afectar al prójimo.":
        "The ASNC promotes and defends respect among people, preserving their integrity and dignity without harming others.",
    "Colaboración dentro de la Ley": "Collaboration within the Law",
    "Somos una entidad que acepta la colaboración y apoyo de terceros en todas sus consideraciones, siempre y cuando estén dentro del marco de la ley y las normas vigentes.":
        "We are an entity that accepts the collaboration and support of third parties in all respects, provided they are within the framework of the law and current regulations.",
    "Inclusión y Apertura": "Inclusion and Openness",
    "Somos una entidad abierta a todos los ciudadanos, profesionales y no profesionales, que quieran y consideren ser parte de los objetivos de la asociación.":
        "We are an entity open to all citizens, professionals and non-professionals, who wish and consider becoming part of the association's objectives.",
    "Espacio Publicitario": "Advertising Space",
    "Impulse su marca junto al": "Boost your brand alongside the",
    "futuro nuclear de Colombia": "nuclear future of Colombia",
    "Asocie su empresa con la comunidad científica y profesional más importante del sector nuclear en Colombia. Ofrecemos espacios de visibilidad en nuestra plataforma, eventos y comunicaciones para organizaciones que comparten nuestra visión de progreso.":
        "Associate your company with the most important scientific and professional community in Colombia's nuclear sector. We offer visibility spaces on our platform, events and communications for organizations that share our vision of progress.",
    "Logo visible en nuestra plataforma web": "Logo displayed on our web platform",
    "Mención en eventos y actividades de la ASNC": "Mention at ASNC events and activities",
    "Presencia en nuestro boletín semanal": "Presence in our weekly newsletter",
    "Contáctenos": "Contact us",
    "Anualidad ASNC": "ASNC Annual Membership",
    "Haz parte del futuro": "Be part of the future",
    "nuclear de Colombia": "nuclear future of Colombia",
    "Como entidad sin ánimo de lucro, cada peso que aportan nuestros asociados se destina directamente a fortalecer la asociación y la comunidad nuclear del país.":
        "As a non-profit entity, every peso contributed by our members goes directly toward strengthening the association and the country's nuclear community.",
    "Organización de eventos, congresos y seminarios": "Organization of events, congresses and seminars",
    "Producción de contenido educativo y divulgación": "Production of educational and outreach content",
    "Representación ante organizaciones internacionales": "Representation before international organizations",
    "Plataformas digitales y herramientas para asociados": "Digital platforms and tools for members",
    "Profesional": "Professional",
    "Profesionales, investigadores y docentes": "Professionals, researchers and educators",
    "COP / año": "COP / year",
    "Incluye:": "Includes:",
    "Carné digital, eventos exclusivos, material especializado, comités técnicos y representación institucional.":
        "Digital card, exclusive events, specialized material, technical committees and institutional representation.",
    "Estudiante": "Student",
    "Pregrado y posgrado en áreas afines": "Undergraduate and graduate students in related fields",
    "Carné digital, acceso a eventos, material educativo y red de contactos profesionales.":
        "Digital card, access to events, educational material and a network of professional contacts.",
    "Solicitar Ingreso a la ASNC": "Apply to Join the ASNC",
    "Únete a Nuestra Comunidad Científica": "Join Our Scientific Community",
    "una de las más importantes del país": "one of the most important in the country",
    "Profesionales, estudiantes y empresas unidos por el desarrollo nuclear pacífico y sostenible de Colombia.":
        "Professionals, students and companies united for the peaceful and sustainable nuclear development of Colombia.",
    "Ayúdanos a ser mejores": "Help us be better",
    "Proceso de revisión: 5-7 días hábiles": "Review process: 5-7 business days",
    "Boletín Semanal": "Weekly Newsletter",
    "No te pierdas ningún avance": "Don't miss any update",
    "Recibe noticias, invitaciones a eventos y artículos destacados de Nuclenergy directamente en tu correo.":
        "Receive news, event invitations and featured articles from Nuclenergy directly in your inbox.",
    "Tu correo electrónico": "Your email address",
    "Suscribirme": "Subscribe",
    "Respetamos tu privacidad. Cero spam.": "We respect your privacy. Zero spam.",
})

# --- about.html ---
TRANSLATIONS.update({
    "Conoce al equipo directivo de la Asociación Nuclear Colombiana (ASNC). Profesionales comprometidos con la divulgación y desarrollo de la ciencia nuclear en Colombia.":
        "Meet the leadership team of the Colombian Nuclear Association (ASNC). Professionals committed to the outreach and development of nuclear science in Colombia.",
    "Nuestra Asociación": "Our Association",
    "La Asociación Nuclear Colombiana (ASNC) reúne a los profesionales, investigadores y entusiastas del sector nuclear en Colombia, promoviendo el desarrollo pacífico y sostenible de la ciencia y tecnología nuclear.":
        "The Colombian Nuclear Association (ASNC) brings together the professionals, researchers, and enthusiasts of the nuclear sector in Colombia, promoting the peaceful and sustainable development of nuclear science and technology.",
    "Misión": "Mission",
    "Albergar y agrupar al gremio nuclear de Colombia, articulando a profesionales, investigadores, estudiantes y empresas del sector en una comunidad sólida que impulse el desarrollo pacífico y sostenible de la ciencia y tecnología nuclear en el país.":
        "To host and unite Colombia's nuclear community, connecting professionals, researchers, students, and companies in the sector within a strong community that drives the peaceful and sustainable development of nuclear science and technology in the country.",
    "Visión 2030": "Vision 2030",
    "Ser el principal punto de encuentro y representación del gremio nuclear colombiano, reconocida como la organización que consolida, conecta y proyecta a la comunidad nuclear del país hacia la región y el mundo.":
        "To be the leading meeting point and representative of the Colombian nuclear community, recognized as the organization that consolidates, connects, and projects the country's nuclear community toward the region and the world.",
    "Valores": "Values",
    "Rigor científico": "Scientific rigor",
    "Transparencia": "Transparency",
    "Educación": "Education",
    "Colaboración": "Collaboration",
    "Nuestra Organización": "Our Organization",
    "Estructura de la ASNC": "ASNC Structure",
    "Una organización sólida construida para cumplir nuestra misión": "A strong organization built to fulfill our mission",
    "Máximo Órgano": "Highest Body",
    "Junta Directiva": "Board of Directors",
    "Gobierno y dirección estratégica de la asociación": "Governance and strategic direction of the association",
    "Comité de Divulgación": "Outreach Committee",
    "Comunicación, contenido educativo y presencia en redes sociales": "Communication, educational content, and social media presence",
    "Comité Científico": "Scientific Committee",
    "Validación científica, investigación y asesoría especializada": "Scientific validation, research, and specialized advisory",
    "Comité de Regulación y Gobierno": "Regulation and Governance Committee",
    "Asuntos regulatorios, políticas públicas y relaciones institucionales": "Regulatory affairs, public policy, and institutional relations",
    "Comité Financiero": "Finance Committee",
    "Gestión de recursos y sostenibilidad económica": "Resource management and economic sustainability",
    "Comité de Educación": "Education Committee",
    "Formación, capacitación y desarrollo académico en ciencia nuclear": "Training, education, and academic development in nuclear science",
    "Comité de Industria y Transporte": "Industry and Transport Committee",
    "Aplicaciones industriales y transporte seguro de material nuclear": "Industrial applications and safe transport of nuclear material",
    "Conócenos": "Get to Know Us",
    "Nuestro Equipo Líder": "Our Leadership Team",
    "Conoce a los profesionales que lideran nuestra asociación": "Meet the professionals who lead our association",
    "Ver perfil completo": "View full profile",
    "Trayectoria Profesional": "Professional Background",
    "Ver perfil en LinkedIn": "View profile on LinkedIn",
    "Próximamente": "Coming Soon",
    "Conocerás a nuestro increíble equipo muy pronto": "You'll meet our amazing team very soon",
    "Red Global": "Global Network",
    "Asociados Internacionales": "International Members",
    "Profesionales y colaboradores alrededor del mundo que fortalecen nuestra misión":
        "Professionals and collaborators around the world who strengthen our mission",
    "Conocerás a nuestros asociados internacionales muy pronto": "You'll meet our international members very soon",
    "¿Quieres ser parte de la ASNC?": "Do you want to be part of ASNC?",
    "Únete a la comunidad científica nuclear más importante de Colombia": "Join the most important nuclear scientific community in Colombia",
    "Solicitar Ingreso": "Apply for Membership",
})

# --- events.html ---
TRANSLATIONS.update({
    "Eventos ASNC": "ASNC Events",
    "Conferencias, talleres, webinars y encuentros para la comunidad nuclear colombiana. Un espacio de aprendizaje y networking.":
        "Conferences, workshops, webinars and gatherings for the Colombian nuclear community. A space for learning and networking.",
    "Estamos preparando algo increíble": "We are preparing something amazing",
    "Nuestro calendario de eventos está en desarrollo. Muy pronto podrás explorar conferencias, talleres y encuentros exclusivos para la comunidad nuclear colombiana.":
        "Our events calendar is under development. Very soon you will be able to explore conferences, workshops and exclusive gatherings for the Colombian nuclear community.",
    "Calendario Interactivo": "Interactive Calendar",
    "Explora y filtra eventos por fecha y categoría": "Browse and filter events by date and category",
    "Inscripción Online": "Online Registration",
    "Regístrate fácilmente a los eventos": "Easily register for events",
    "Notificaciones": "Notifications",
    "Recibe alertas de nuevos eventos": "Receive alerts about new events",
    "Lo que viene": "What's Coming",
    "Tipos de Eventos": "Event Types",
    "Diversas actividades para todos los interesados en el sector nuclear": "Diverse activities for everyone interested in the nuclear sector",
    "Conferencias": "Conferences",
    "Ponencias de expertos nacionales e internacionales sobre avances en tecnología nuclear":
        "Presentations by national and international experts on advances in nuclear technology",
    "Presencial & Virtual": "In-Person & Virtual",
    "Webinars": "Webinars",
    "Sesiones en línea sobre temas específicos con interacción en tiempo real": "Online sessions on specific topics with real-time interaction",
    "100% Online": "100% Online",
    "Talleres": "Workshops",
    "Formación práctica y especializada para profesionales del sector": "Practical and specialized training for sector professionals",
    "Hands-on": "Hands-on",
    "Networking": "Networking",
    "Encuentros para conectar con profesionales y expandir tu red de contactos": "Gatherings to connect with professionals and expand your network",
    "Comunidad": "Community",
    "¿Quieres ser el primero en enterarte?": "Want to be the first to know?",
    "Únete a la ASNC y recibe notificaciones de todos nuestros eventos": "Join the ASNC and receive notifications about all our events",
    "Unirme a la ASNC": "Join the ASNC",
})

# --- privacy_policy.html ---
TRANSLATIONS.update({
    "Política de Privacidad y Tratamiento de Datos": "Privacy and Data Processing Policy",
    "Política de privacidad y tratamiento de datos personales de la Asociación Nuclear Colombiana (ASNC). Conoce cómo protegemos tu información.":
        "Privacy and personal data processing policy of the Colombian Nuclear Association (ASNC). Learn how we protect your information.",
    "Documento Legal": "Legal Document",
    "Política de Privacidad y Tratamiento de Datos Personales": "Personal Data Privacy and Processing Policy",
    "Última actualización: Marzo 2026": "Last updated: March 2026",
    "Bucaramanga, Santander, Colombia": "Bucaramanga, Santander, Colombia",
    "Contenido": "Contents",
    "Identificación del Responsable": "Identification of the Data Controller",
    "Marco Legal Aplicable": "Applicable Legal Framework",
    "Definiciones": "Definitions",
    "Principios Rectores": "Guiding Principles",
    "Datos Personales Recolectados": "Personal Data Collected",
    "Finalidad del Tratamiento": "Purpose of Processing",
    "Autorización del Titular": "Data Subject's Authorization",
    "Derechos de los Titulares": "Rights of Data Subjects",
    "Procedimiento para Ejercer Derechos": "Procedure to Exercise Rights",
    "Medidas de Seguridad": "Security Measures",
    "Transferencia y Transmisión de Datos": "Data Transfer and Transmission",
    "Cookies y Tecnologías de Rastreo": "Cookies and Tracking Technologies",
    "Conservación de los Datos": "Data Retention",
    "Tratamiento de Datos de Menores": "Processing of Minors' Data",
    "Modificaciones a la Política": "Amendments to the Policy",
    "Canal de Atención y Contacto": "Support and Contact Channel",
    "1. Identificación del Responsable del Tratamiento": "1. Identification of the Data Controller",
    "Razón social:": "Legal name:",
    "NIT:": "Tax ID (NIT):",
    "Naturaleza jurídica:": "Legal nature:",
    "Entidad sin ánimo de lucro": "Non-profit entity",
    "Domicilio:": "Address:",
    "Correo electrónico:": "Email:",
    "Sitio web:": "Website:",
    "La Asociación Nuclear Colombiana (en adelante \"ASNC\" o \"la Asociación\"), en su calidad de Responsable del Tratamiento de datos personales, manifiesta su compromiso con la protección de la privacidad y los datos personales de sus asociados, aspirantes, colaboradores, aliados y demás personas naturales con quienes mantiene o ha mantenido alguna relación. La presente política establece los lineamientos bajo los cuales la ASNC recolecta, almacena, usa, circula, suprime y, en general, trata datos personales.":
        "The Colombian Nuclear Association (hereinafter \"ASNC\" or \"the Association\"), in its capacity as Data Controller of personal data, expresses its commitment to protecting the privacy and personal data of its members, applicants, collaborators, partners and other natural persons with whom it maintains or has maintained any relationship. This policy establishes the guidelines under which the ASNC collects, stores, uses, circulates, deletes and, in general, processes personal data.",
    "2. Marco Legal Aplicable": "2. Applicable Legal Framework",
    "La presente política se rige por la normatividad colombiana vigente en materia de protección de datos personales, en particular:":
        "This policy is governed by the Colombian regulations in force regarding the protection of personal data, in particular:",
    "Constitución Política de Colombia, Artículo 15:": "Political Constitution of Colombia, Article 15:",
    "Derecho fundamental a la intimidad, al buen nombre y al habeas data.": "Fundamental right to privacy, good name and habeas data.",
    "Ley Estatutaria 1581 de 2012:": "Statutory Law 1581 of 2012:",
    "Régimen General de Protección de Datos Personales, por la cual se dictan disposiciones generales para la protección de datos personales.":
        "General Personal Data Protection Regime, which sets out general provisions for the protection of personal data.",
    "Decreto 1377 de 2013 (compilado en el Decreto 1074 de 2015):": "Decree 1377 of 2013 (compiled in Decree 1074 of 2015):",
    "Reglamenta parcialmente la Ley 1581 de 2012 en aspectos relacionados con la autorización del titular, las políticas de tratamiento, el ejercicio de derechos y las transferencias de datos.":
        "Partially regulates Law 1581 of 2012 in aspects related to the data subject's authorization, processing policies, the exercise of rights and data transfers.",
    "Decreto 1074 de 2015, Libro 2, Parte 2, Título 4:": "Decree 1074 of 2015, Book 2, Part 2, Title 4:",
    "Decreto Único Reglamentario del Sector Comercio, Industria y Turismo en materia de datos personales.":
        "Single Regulatory Decree of the Commerce, Industry and Tourism Sector regarding personal data.",
    "Sentencia C-748 de 2011 de la Corte Constitucional:": "Ruling C-748 of 2011 of the Constitutional Court:",
    "Control de constitucionalidad de la Ley 1581 de 2012.": "Constitutional review of Law 1581 of 2012.",
    "3. Definiciones": "3. Definitions",
    "Para efectos de la presente política, se adoptan las siguientes definiciones conforme a la Ley 1581 de 2012 y sus decretos reglamentarios:":
        "For the purposes of this policy, the following definitions are adopted in accordance with Law 1581 of 2012 and its implementing decrees:",
    "Autorización": "Authorization",
    "Consentimiento previo, expreso e informado del Titular para llevar a cabo el Tratamiento de datos personales.":
        "The data subject's prior, express and informed consent to carry out the Processing of personal data.",
    "Base de Datos": "Database",
    "Conjunto organizado de datos personales que sea objeto de Tratamiento.": "An organized set of personal data that is subject to Processing.",
    "Dato Personal": "Personal Data",
    "Cualquier información vinculada o que pueda asociarse a una o varias personas naturales determinadas o determinables.":
        "Any information linked to or that may be associated with one or several specific or identifiable natural persons.",
    "Dato Sensible": "Sensitive Data",
    "Dato que afecta la intimidad del Titular o cuyo uso indebido puede generar discriminación, tales como aquellos que revelen el origen racial o étnico, orientación política, convicciones religiosas o filosóficas, pertenencia a sindicatos, organizaciones sociales, datos relativos a la salud, vida sexual y datos biométricos.":
        "Data that affects the data subject's privacy or whose improper use may lead to discrimination, such as data revealing racial or ethnic origin, political orientation, religious or philosophical beliefs, membership in trade unions or social organizations, data relating to health, sex life and biometric data.",
    "Encargado del Tratamiento": "Data Processor",
    "Persona natural o jurídica, pública o privada, que por sí misma o en asocio con otros, realice el Tratamiento de datos personales por cuenta del Responsable del Tratamiento.":
        "A natural or legal person, public or private, who, by themselves or in association with others, carries out the Processing of personal data on behalf of the Data Controller.",
    "Responsable del Tratamiento": "Data Controller",
    "Persona natural o jurídica, pública o privada, que por sí misma o en asocio con otros, decida sobre la base de datos y/o el Tratamiento de los datos.":
        "A natural or legal person, public or private, who, by themselves or in association with others, decides on the database and/or the Processing of the data.",
    "Titular": "Data Subject",
    "Persona natural cuyos datos personales sean objeto de Tratamiento.": "A natural person whose personal data is subject to Processing.",
    "Tratamiento": "Processing",
    "Cualquier operación o conjunto de operaciones sobre datos personales, tales como la recolección, almacenamiento, uso, circulación o supresión.":
        "Any operation or set of operations on personal data, such as collection, storage, use, circulation or deletion.",
    "Transferencia": "Transfer",
    "La transferencia de datos tiene lugar cuando el Responsable y/o Encargado del Tratamiento de datos personales envía la información o los datos personales a un receptor, que a su vez es Responsable del Tratamiento, y se encuentra dentro o fuera del país.":
        "A data transfer takes place when the Data Controller and/or Data Processor of personal data sends the information or personal data to a recipient, who is in turn a Data Controller, and who is located inside or outside the country.",
    "Transmisión": "Transmission",
    "Tratamiento de datos personales que implica la comunicación de los mismos dentro o fuera del territorio colombiano, cuando tenga por objeto la realización de un Tratamiento por el Encargado por cuenta del Responsable.":
        "Processing of personal data involving its communication inside or outside Colombian territory, when the purpose is the carrying out of Processing by the Data Processor on behalf of the Data Controller.",
    "4. Principios Rectores del Tratamiento": "4. Guiding Principles of Processing",
    "La ASNC aplicará los siguientes principios en el tratamiento de datos personales, de conformidad con el artículo 4 de la Ley 1581 de 2012:":
        "The ASNC will apply the following principles in the processing of personal data, in accordance with Article 4 of Law 1581 of 2012:",
    "Legalidad": "Legality",
    "El tratamiento es una actividad reglada que se sujeta a la Constitución, la ley y las demás disposiciones que la desarrollen.":
        "Processing is a regulated activity subject to the Constitution, the law and the other provisions that develop it.",
    "Finalidad": "Purpose",
    "El tratamiento obedece a una finalidad legítima, la cual será informada al Titular de manera previa.":
        "Processing serves a legitimate purpose, which will be communicated to the data subject in advance.",
    "Libertad": "Freedom",
    "El tratamiento solo puede ejercerse con el consentimiento previo, expreso e informado del Titular.":
        "Processing may only be carried out with the prior, express and informed consent of the data subject.",
    "Veracidad": "Accuracy",
    "La información sujeta a tratamiento debe ser veraz, completa, exacta, actualizada y comprobable.":
        "Information subject to processing must be truthful, complete, accurate, up-to-date and verifiable.",
    "Se garantiza el derecho del Titular a obtener información acerca de la existencia de datos que le conciernan.":
        "The data subject's right to obtain information about the existence of data concerning them is guaranteed.",
    "Seguridad": "Security",
    "La información se manejará con las medidas técnicas, humanas y administrativas necesarias para otorgar seguridad.":
        "Information will be handled with the technical, human and administrative measures necessary to ensure security.",
    "Confidencialidad": "Confidentiality",
    "Todas las personas que intervengan en el tratamiento están obligadas a garantizar la reserva de la información.":
        "All persons involved in the processing are obliged to ensure the confidentiality of the information.",
    "Acceso y circulación restringida": "Restricted access and circulation",
    "El tratamiento se sujeta a los límites derivados de la naturaleza de los datos y de la autorización del Titular.":
        "Processing is subject to the limits arising from the nature of the data and the data subject's authorization.",
    "5. Datos Personales Recolectados": "5. Personal Data Collected",
    "En el desarrollo de su objeto social y actividades misionales, la ASNC podrá recolectar las siguientes categorías de datos personales:":
        "In the course of its corporate purpose and mission-related activities, the ASNC may collect the following categories of personal data:",
    "5.1. Datos de identificación y contacto": "5.1. Identification and contact data",
    "Nombres y apellidos completos": "Full first and last names",
    "Correo electrónico personal e institucional": "Personal and institutional email address",
    "Número de teléfono o celular": "Telephone or mobile number",
    "Ciudad y país de residencia": "City and country of residence",
    "5.2. Datos profesionales y académicos": "5.2. Professional and academic data",
    "Profesión y título académico": "Profession and academic degree",
    "Cargo o posición actual": "Current role or position",
    "Institución o empresa donde labora": "Institution or company where employed",
    "Perfil profesional en LinkedIn": "LinkedIn professional profile",
    "Hoja de vida o currículum vitae": "Resume or curriculum vitae",
    "Biografía profesional": "Professional biography",
    "5.3. Datos de la membresía": "5.3. Membership data",
    "Número de carné de asociado": "Member card number",
    "Categoría de membresía (Fundador, Asociado, Estudiante, Profesional)": "Membership category (Founder, Associate, Student, Professional)",
    "Fecha de ingreso y vigencia": "Date of joining and validity",
    "Estado de la membresía": "Membership status",
    "Fotografía del asociado (para el carné digital)": "Member's photograph (for the digital card)",
    "5.4. Datos de navegación y uso de la plataforma": "5.4. Browsing and platform usage data",
    "Dirección IP": "IP address",
    "Tipo de navegador y dispositivo": "Browser and device type",
    "Páginas visitadas y tiempo de permanencia": "Pages visited and time spent",
    "Datos recopilados mediante cookies y Google Analytics": "Data collected through cookies and Google Analytics",
    "Datos sensibles:": "Sensitive data:",
    "La ASNC no recolecta datos sensibles de manera deliberada. En caso de que, por la naturaleza de alguna actividad, fuese necesario tratar datos de esta categoría, se solicitará autorización expresa y específica al Titular conforme al artículo 6 de la Ley 1581 de 2012, informando el carácter facultativo de la respuesta.":
        "The ASNC does not deliberately collect sensitive data. Should it be necessary, due to the nature of an activity, to process data in this category, express and specific authorization will be requested from the data subject in accordance with Article 6 of Law 1581 of 2012, informing them that the response is optional.",
    "6. Finalidad del Tratamiento": "6. Purpose of Processing",
    "Los datos personales recolectados por la ASNC serán utilizados para las siguientes finalidades:":
        "The personal data collected by the ASNC will be used for the following purposes:",
    "6.1. Finalidades relacionadas con la membresía": "6.1. Membership-related purposes",
    "Gestionar y tramitar las solicitudes de ingreso a la Asociación.": "Manage and process applications to join the Association.",
    "Verificar la identidad y los requisitos de los aspirantes a asociados.": "Verify the identity and requirements of membership applicants.",
    "Emitir y administrar los carnés digitales de asociado.": "Issue and manage digital member cards.",
    "Mantener actualizado el directorio oficial de asociados.": "Keep the official member directory up to date.",
    "Gestionar el cobro y registro de la anualidad de membresía.": "Manage the collection and recording of the annual membership fee.",
    "Clasificar a los asociados según su categoría (Profesional, Estudiante, Fundador).": "Classify members according to their category (Professional, Student, Founder).",
    "6.2. Finalidades de comunicación": "6.2. Communication purposes",
    "Enviar comunicaciones institucionales, boletines informativos y noticias del sector nuclear.": "Send institutional communications, newsletters and news from the nuclear sector.",
    "Informar sobre eventos, congresos, seminarios y actividades de la Asociación.": "Provide information about events, conferences, seminars and activities of the Association.",
    "Notificar cambios en los estatutos, políticas o condiciones de la membresía.": "Notify changes to the bylaws, policies or membership conditions.",
    "Remitir correos electrónicos relacionados con el estado de la cuenta del asociado.": "Send emails related to the status of the member's account.",
    "6.3. Finalidades institucionales": "6.3. Institutional purposes",
    "Cumplir con el objeto social de la Asociación como entidad sin ánimo de lucro.": "Fulfill the corporate purpose of the Association as a non-profit entity.",
    "Elaborar estadísticas internas con fines de mejora continua.": "Compile internal statistics for continuous improvement purposes.",
    "Representar a los asociados ante organizaciones nacionales e internacionales.": "Represent members before national and international organizations.",
    "Gestionar alianzas con instituciones académicas, científicas y gremiales.": "Manage alliances with academic, scientific and trade institutions.",
    "Cumplir obligaciones legales y regulatorias ante las autoridades colombianas.": "Comply with legal and regulatory obligations before the Colombian authorities.",
    "6.4. Finalidades de la plataforma digital": "6.4. Digital platform purposes",
    "Administrar el acceso al portal de asociados (mi-portal).": "Manage access to the members' portal (mi-portal).",
    "Generar y verificar carnés digitales mediante códigos QR.": "Generate and verify digital cards using QR codes.",
    "Permitir la actualización del perfil profesional del asociado.": "Allow members to update their professional profile.",
    "Mejorar la experiencia de navegación y funcionalidad del sitio web.": "Improve the browsing experience and functionality of the website.",
    "Analizar el tráfico web mediante herramientas de analítica (Google Analytics).": "Analyze web traffic using analytics tools (Google Analytics).",
    "7. Autorización del Titular": "7. Data Subject's Authorization",
    "De conformidad con los artículos 9 y 10 de la Ley 1581 de 2012, la ASNC obtendrá la autorización previa, expresa e informada del Titular para el tratamiento de sus datos personales. Esta autorización podrá otorgarse a través de los siguientes mecanismos:":
        "In accordance with Articles 9 and 10 of Law 1581 of 2012, the ASNC will obtain the data subject's prior, express and informed authorization for the processing of their personal data. This authorization may be granted through the following mechanisms:",
    "Formulario de solicitud de ingreso:": "Membership application form:",
    "Al diligenciar el formulario de vinculación a través del sitio web www.asncol.com, el aspirante autoriza expresamente el tratamiento de los datos allí consignados.":
        "By completing the membership form through the website www.asncol.com, the applicant expressly authorizes the processing of the data provided therein.",
    "Aceptación electrónica:": "Electronic acceptance:",
    "Mediante la aceptación de los términos y condiciones y la política de privacidad en los formularios digitales.":
        "By accepting the terms and conditions and the privacy policy in the digital forms.",
    "Comunicación escrita o electrónica:": "Written or electronic communication:",
    "A través de correo electrónico u otro medio verificable dirigido a info@asncol.com.": "Through email or another verifiable means addressed to info@asncol.com.",
    "La autorización podrá ser revocada en cualquier momento por el Titular, salvo que exista un deber legal o contractual que imponga al Titular la obligación de permanecer en la base de datos. La revocación se solicitará mediante los canales indicados en la sección 9 de la presente política.":
        "The authorization may be revoked at any time by the data subject, unless there is a legal or contractual duty requiring the data subject to remain in the database. Revocation must be requested through the channels indicated in Section 9 of this policy.",
    "Excepción legal:": "Legal exception:",
    "Conforme al artículo 10 de la Ley 1581 de 2012, no será necesaria la autorización cuando se trate de información requerida por una entidad pública o administrativa en ejercicio de sus funciones legales, datos de naturaleza pública, casos de urgencia médica o sanitaria, o tratamiento autorizado por la ley para fines históricos, estadísticos o científicos.":
        "In accordance with Article 10 of Law 1581 of 2012, authorization will not be required for information requested by a public or administrative entity in the exercise of its legal functions, data of a public nature, medical or health emergencies, or processing authorized by law for historical, statistical or scientific purposes.",
    "8. Derechos de los Titulares": "8. Rights of Data Subjects",
    "De conformidad con el artículo 8 de la Ley 1581 de 2012, los Titulares de los datos personales tendrán los siguientes derechos:":
        "In accordance with Article 8 of Law 1581 of 2012, data subjects shall have the following rights:",
    "Conocer": "Know",
    "Conocer, actualizar y rectificar sus datos personales frente a la ASNC. Este derecho podrá ejercerse, entre otros, frente a datos parciales, inexactos, incompletos, fraccionados, que induzcan a error, o aquellos cuyo tratamiento esté expresamente prohibido o no haya sido autorizado.":
        "Know, update and rectify their personal data held by the ASNC. This right may be exercised, among others, in respect of partial, inaccurate, incomplete or fragmented data, data that is misleading, or data whose processing is expressly prohibited or has not been authorized.",
    "Solicitar prueba": "Request proof",
    "Solicitar prueba de la autorización otorgada a la ASNC, salvo cuando expresamente se exceptúe como requisito para el tratamiento conforme a la ley.":
        "Request proof of the authorization granted to the ASNC, except when it is expressly exempted as a requirement for processing under the law.",
    "Ser informado": "Be informed",
    "Ser informado por la ASNC, previa solicitud, respecto del uso que se le ha dado a sus datos personales.":
        "Be informed by the ASNC, upon request, of how their personal data has been used.",
    "Presentar quejas": "File complaints",
    "Presentar ante la Superintendencia de Industria y Comercio (SIC) quejas por infracciones a lo dispuesto en la Ley 1581 de 2012 y demás normas que la modifiquen, adicionen o complementen.":
        "File complaints with the Superintendence of Industry and Commerce (SIC) for violations of the provisions of Law 1581 of 2012 and other regulations that amend, add to or supplement it.",
    "Revocar y suprimir": "Revoke and delete",
    "Revocar la autorización y/o solicitar la supresión del dato cuando en el tratamiento no se respeten los principios, derechos y garantías constitucionales y legales.":
        "Revoke the authorization and/or request the deletion of the data when the processing does not respect the constitutional and legal principles, rights and guarantees.",
    "Acceso gratuito": "Free access",
    "Acceder en forma gratuita a sus datos personales que hayan sido objeto de tratamiento.": "Access free of charge their personal data that has been subject to processing.",
    "9. Procedimiento para Ejercer los Derechos": "9. Procedure to Exercise Rights",
    "El Titular o sus causahabientes podrán ejercer sus derechos mediante comunicación escrita dirigida a la ASNC a través de los siguientes canales:":
        "The data subject or their successors may exercise their rights by means of a written communication addressed to the ASNC through the following channels:",
    "Asunto sugerido:": "Suggested subject line:",
    "\"Solicitud de Habeas Data - [Tipo de solicitud]\"": "\"Habeas Data Request - [Type of request]\"",
    "La solicitud deberá contener como mínimo:": "The request must contain at least:",
    "Nombre completo y documento de identificación del Titular.": "Full name and identification document of the data subject.",
    "Descripción clara y precisa de los datos respecto de los cuales se busca ejercer algún derecho.": "A clear and precise description of the data in respect of which a right is sought to be exercised.",
    "Descripción de los hechos que dan lugar a la solicitud.": "A description of the facts giving rise to the request.",
    "Dirección de correspondencia (física o electrónica) y datos de contacto.": "Mailing address (physical or electronic) and contact details.",
    "Documentos que soporten la solicitud, cuando aplique.": "Documents supporting the request, where applicable.",
    "Plazos de respuesta": "Response times",
    "De conformidad con la Ley 1581 de 2012:": "In accordance with Law 1581 of 2012:",
    "Consultas (Art. 14):": "Inquiries (Art. 14):",
    "Serán atendidas en un término máximo de diez (10) días hábiles contados a partir de la fecha de recibo de la solicitud. Cuando no fuere posible atenderla dentro de dicho término, se informará al interesado antes del vencimiento de los diez (10) días, expresando los motivos de la demora y señalando la fecha en que se atenderá, la cual en ningún caso podrá superar los cinco (5) días hábiles siguientes al vencimiento del primer término.":
        "Will be addressed within a maximum period of ten (10) business days from the date the request is received. When it is not possible to address it within that period, the interested party will be informed before the expiration of the ten (10) days, stating the reasons for the delay and indicating the date on which it will be addressed, which in no case may exceed five (5) business days following the expiration of the first period.",
    "Reclamos (Art. 15):": "Claims (Art. 15):",
    "Serán atendidos en un término máximo de quince (15) días hábiles contados a partir del día siguiente a la fecha de recibo. Cuando no fuere posible atenderlo dentro de dicho término, se informará al interesado los motivos de la demora y la fecha en que se atenderá su reclamo, la cual en ningún caso podrá superar los ocho (8) días hábiles siguientes al vencimiento del primer término.":
        "Will be addressed within a maximum period of fifteen (15) business days from the day following the date of receipt. When it is not possible to address it within that period, the interested party will be informed of the reasons for the delay and the date on which their claim will be addressed, which in no case may exceed eight (8) business days following the expiration of the first period.",
    "10. Medidas de Seguridad": "10. Security Measures",
    "La ASNC adopta las medidas técnicas, humanas y administrativas necesarias para garantizar la seguridad de los datos personales, evitando su adulteración, pérdida, consulta, uso o acceso no autorizado o fraudulento, de conformidad con el artículo 17, literal (d) de la Ley 1581 de 2012.":
        "The ASNC adopts the technical, human and administrative measures necessary to guarantee the security of personal data, preventing its alteration, loss, unauthorized or fraudulent consultation, use or access, in accordance with Article 17, paragraph (d) of Law 1581 of 2012.",
    "Entre las medidas implementadas se encuentran:": "The measures implemented include:",
    "Protección técnica:": "Technical protection:",
    "Uso de protocolos de comunicación cifrados (HTTPS/SSL), almacenamiento seguro en infraestructura en la nube (Amazon Web Services - AWS), protección CSRF en todos los formularios y tokens de acceso con expiración temporal.":
        "Use of encrypted communication protocols (HTTPS/SSL), secure storage in cloud infrastructure (Amazon Web Services - AWS), CSRF protection on all forms and access tokens with time-based expiration.",
    "Control de acceso:": "Access control:",
    "Autenticación basada en correo electrónico, gestión de permisos por roles (administrador, staff, asociado), y protección contra eliminación accidental de registros críticos.":
        "Email-based authentication, role-based permission management (administrator, staff, member), and protection against accidental deletion of critical records.",
    "Integridad de datos:": "Data integrity:",
    "Uso de transacciones atómicas en operaciones críticas y protección contra condiciones de carrera en la base de datos.":
        "Use of atomic transactions in critical operations and protection against race conditions in the database.",
    "Medidas administrativas:": "Administrative measures:",
    "Acceso restringido a las bases de datos únicamente al personal autorizado de la Junta Directiva y designados por esta.":
        "Access to the databases restricted solely to personnel authorized by, and designated by, the Board of Directors.",
    "11. Transferencia y Transmisión de Datos": "11. Data Transfer and Transmission",
    "La ASNC podrá realizar transferencia o transmisión de datos personales en los siguientes casos, garantizando siempre el cumplimiento de los principios y obligaciones establecidos en la Ley 1581 de 2012:":
        "The ASNC may carry out the transfer or transmission of personal data in the following cases, always ensuring compliance with the principles and obligations established in Law 1581 of 2012:",
    "Proveedores de servicios tecnológicos:": "Technology service providers:",
    "Los datos podrán ser almacenados en servidores de Amazon Web Services (AWS) ubicados fuera del territorio colombiano, bajo contratos que garantizan niveles adecuados de protección conforme a los estándares internacionales y la legislación colombiana.":
        "Data may be stored on Amazon Web Services (AWS) servers located outside Colombian territory, under contracts that guarantee adequate levels of protection in accordance with international standards and Colombian legislation.",
    "Organizaciones aliadas:": "Partner organizations:",
    "Cuando sea necesario para el cumplimiento de convenios interinstitucionales con organizaciones científicas y académicas, nacionales o internacionales, previa autorización del Titular.":
        "When necessary to fulfill inter-institutional agreements with scientific and academic organizations, whether national or international, subject to the prior authorization of the data subject.",
    "Autoridades competentes:": "Competent authorities:",
    "Cuando sea requerido por autoridades judiciales o administrativas en ejercicio de sus funciones legales.": "When required by judicial or administrative authorities in the exercise of their legal functions.",
    "En ningún caso la ASNC venderá, alquilará o comercializará los datos personales de sus asociados o de cualquier persona natural a terceros con fines comerciales.":
        "Under no circumstances will the ASNC sell, rent or trade the personal data of its members or of any natural person to third parties for commercial purposes.",
    "12. Cookies y Tecnologías de Rastreo": "12. Cookies and Tracking Technologies",
    "El sitio web www.asncol.com utiliza las siguientes tecnologías:": "The website www.asncol.com uses the following technologies:",
    "12.1. Cookies esenciales": "12.1. Essential cookies",
    "Necesarias para el funcionamiento básico del sitio web, incluyendo la gestión de sesiones de usuario, protección CSRF y preferencias de navegación. Estas cookies no requieren consentimiento adicional ya que son estrictamente necesarias para la prestación del servicio.":
        "Necessary for the basic functioning of the website, including user session management, CSRF protection and browsing preferences. These cookies do not require additional consent as they are strictly necessary for the provision of the service.",
    "12.2. Google Analytics": "12.2. Google Analytics",
    "El sitio utiliza Google Analytics 4 (identificador: G-1H2FNJ5PB8) para analizar el tráfico web y mejorar la experiencia del usuario. Esta herramienta recopila información anonimizada sobre las páginas visitadas, el tiempo de permanencia, el tipo de dispositivo y la ubicación geográfica general. Los datos recopilados son tratados conforme a la":
        "The site uses Google Analytics 4 (identifier: G-1H2FNJ5PB8) to analyze web traffic and improve the user experience. This tool collects anonymized information about the pages visited, time spent, device type and general geographic location. The data collected is processed in accordance with the",
    "Política de Privacidad de Google": "Google Privacy Policy",
    "El usuario puede deshabilitar las cookies de Google Analytics instalando el": "Users can disable Google Analytics cookies by installing the",
    "complemento de inhabilitación": "opt-out add-on",
    "proporcionado por Google, o configurando las preferencias de su navegador.": "provided by Google, or by configuring their browser preferences.",
    "13. Conservación de los Datos": "13. Data Retention",
    "Los datos personales serán conservados por el tiempo necesario para cumplir con las finalidades descritas en la presente política, y de acuerdo con los siguientes criterios:":
        "Personal data will be retained for the time necessary to fulfill the purposes described in this policy, and in accordance with the following criteria:",
    "Asociados activos:": "Active members:",
    "Mientras subsista la relación de membresía con la Asociación y no se solicite la supresión.": "As long as the membership relationship with the Association subsists and deletion is not requested.",
    "Solicitudes de ingreso:": "Membership applications:",
    "Los datos de las solicitudes no aprobadas serán conservados por un periodo de un (1) año contado a partir de la decisión, con fines estadísticos y de trazabilidad.":
        "The data of applications that are not approved will be retained for a period of one (1) year from the decision, for statistical and traceability purposes.",
    "Ex-asociados:": "Former members:",
    "Los datos básicos de identificación podrán ser conservados con fines históricos y de registro institucional, conforme a los estatutos de la Asociación.":
        "Basic identification data may be retained for historical and institutional record-keeping purposes, in accordance with the Association's bylaws.",
    "Obligaciones legales:": "Legal obligations:",
    "Cuando exista una obligación legal o regulatoria que exija la conservación de los datos por un periodo determinado, estos serán mantenidos por el tiempo requerido por la norma aplicable.":
        "When there is a legal or regulatory obligation requiring the retention of data for a specific period, it will be kept for the time required by the applicable regulation.",
    "Cumplida la finalidad del tratamiento y agotados los términos legales de conservación, la ASNC procederá a la supresión de los datos personales de sus archivos y bases de datos, adoptando las medidas necesarias para su eliminación segura.":
        "Once the purpose of the processing has been fulfilled and the legal retention periods have expired, the ASNC will proceed to delete the personal data from its files and databases, adopting the measures necessary for its secure deletion.",
    "14. Tratamiento de Datos de Menores de Edad": "14. Processing of Minors' Data",
    "De conformidad con el artículo 7 de la Ley 1581 de 2012 y la jurisprudencia de la Corte Constitucional, la ASNC no recolecta ni trata de manera deliberada datos personales de niños, niñas y adolescentes.":
        "In accordance with Article 7 of Law 1581 of 2012 and the case law of the Constitutional Court, the ASNC does not deliberately collect or process the personal data of children and adolescents.",
    "El formulario de solicitud de ingreso y los servicios de la plataforma digital están diseñados para ser utilizados exclusivamente por personas mayores de edad. En caso de que la ASNC identifique que se han recolectado datos de un menor de edad sin la autorización correspondiente de su representante legal, procederá a la supresión inmediata de dicha información.":
        "The membership application form and the digital platform services are designed to be used exclusively by persons of legal age. Should the ASNC identify that a minor's data has been collected without the corresponding authorization of their legal representative, it will proceed to immediately delete such information.",
    "15. Modificaciones a la Política": "15. Amendments to the Policy",
    "La ASNC se reserva el derecho de modificar la presente Política de Privacidad y Tratamiento de Datos Personales en cualquier momento, conforme a la normatividad vigente. Cualquier cambio sustancial será comunicado a los Titulares a través de los siguientes medios:":
        "The ASNC reserves the right to amend this Personal Data Privacy and Processing Policy at any time, in accordance with the regulations in force. Any substantial change will be communicated to data subjects through the following means:",
    "Publicación de la versión actualizada en el sitio web www.asncol.com.": "Publication of the updated version on the website www.asncol.com.",
    "Comunicación por correo electrónico a los asociados activos, cuando la modificación afecte directamente el tratamiento de sus datos.":
        "Email communication to active members when the change directly affects the processing of their data.",
    "La fecha de la última actualización se indicará siempre en el encabezado del documento. El uso continuado de los servicios de la ASNC con posterioridad a la publicación de las modificaciones constituirá aceptación de las mismas.":
        "The date of the last update will always be indicated in the header of the document. Continued use of the ASNC's services after the publication of the amendments will constitute acceptance of them.",
    "16. Canal de Atención y Contacto": "16. Support and Contact Channel",
    "Para cualquier consulta, reclamo o solicitud relacionada con el tratamiento de datos personales, los Titulares podrán comunicarse con la ASNC a través de los siguientes canales:":
        "For any inquiry, claim or request related to the processing of personal data, data subjects may contact the ASNC through the following channels:",
    "Responsable:": "Data Controller:",
    "Autoridad de control:": "Supervisory authority:",
    "Superintendencia de Industria y Comercio (SIC) - www.sic.gov.co": "Superintendence of Industry and Commerce (SIC) - www.sic.gov.co",
    "La presente Política de Privacidad y Tratamiento de Datos Personales fue aprobada por la Junta Directiva de la Asociación Nuclear Colombiana y entra en vigencia a partir de su publicación en el sitio web www.asncol.com.":
        "This Personal Data Privacy and Processing Policy was approved by the Board of Directors of the Colombian Nuclear Association and takes effect upon its publication on the website www.asncol.com.",
})

# --- news/list.html + news/detail.html + convocatorias public ---
TRANSLATIONS.update({
    "Noticias y novedades de la Asociación Nuclear Colombiana (ASNC). Mantente informado sobre el sector nuclear en Colombia.":
        "News and updates from the Colombian Nuclear Association (ASNC). Stay informed about the nuclear sector in Colombia.",
    "Blog ASNC": "ASNC Blog",
    "Noticias y Novedades": "News and Updates",
    "Lo último del sector nuclear colombiano y la comunidad ASNC": "The latest from the Colombian nuclear sector and the ASNC community",
    "Leer más": "Read more",
    "Estamos preparando contenido para ti. ¡Vuelve pronto!": "We are preparing content for you. Come back soon!",
    "Todas las noticias": "All news",
    "Compartir:": "Share:",
    "Más noticias": "More news",
    "Convocatorias": "Calls for Applications",
    "Convocatorias abiertas de la Asociación Nuclear Colombiana. Inscríbete a programas, eventos y oportunidades para la comunidad nuclear.":
        "Open calls for applications from the Colombian Nuclear Association. Register for programs, events, and opportunities for the nuclear community.",
    "Participa en las iniciativas abiertas de la ASNC": "Take part in ASNC's open initiatives",
    "Abierta": "Open",
    "Cierra:": "Closes:",
    "No hay convocatorias activas": "There are no active calls for applications",
    "Vuelve pronto para ver nuevas oportunidades.": "Check back soon to see new opportunities.",
    "Todas las convocatorias": "All calls for applications",
    "Inscripciones abiertas": "Registration open",
    "Cerrada": "Closed",
    "Apertura": "Opening",
    "Cierre": "Closing",
    "Formulario de inscripción": "Registration form",
    "Completa los siguientes datos. Los campos con * son obligatorios.": "Complete the following information. Fields marked with * are required.",
    "Enviar inscripción": "Submit registration",
    "Esta convocatoria aún no tiene un formulario configurado.": "This call for applications does not yet have a form configured.",
    "Las inscripciones no están disponibles en este momento.": "Registration is not available at this time.",
    "Inscripción enviada": "Registration submitted",
    "Tu inscripción a %(convocatoria.title)s ha sido recibida correctamente.": "Your registration for %(convocatoria.title)s has been received successfully.",
    "¡Gracias!": "Thank you!",
    "Tu inscripción ha sido recibida": "Your registration has been received",
    "Ver más convocatorias": "View more calls for applications",
    "Volver al inicio": "Back to home",
})

# --- application_form.html + application_success.html + carnets/verificar.html ---
TRANSLATIONS.update({
    "Forma parte de la comunidad nuclear más importante de Colombia": "Be part of Colombia's most important nuclear community",
    "Nombres": "First Name",
    "Apellidos": "Last Name",
    "Correo electrónico": "Email",
    "Teléfono": "Phone",
    "Profesión": "Profession",
    "Acepto la": "I accept the",
    "política de privacidad": "privacy policy",
    "y el tratamiento de mis datos": "and the processing of my data",
    "Enviar solicitud": "Submit application",
    "¿Ya eres miembro?": "Already a member?",
    "Inicia sesión": "Log in",
    "Solicitud Recibida - ASNC": "Application Received - ASNC",
    "¡Solicitud Recibida!": "Application Received!",
    "Gracias por tu interés en formar parte de la": "Thank you for your interest in becoming part of the",
    "Te enviaremos un correo de confirmación": "We will send you a confirmation email",
    "Nuestro Comité revisará tu perfil": "Our Committee will review your profile",
    "Recibirás respuesta en los próximos días": "You will receive a response in the coming days",
    "La ciencia nuclear al servicio del desarrollo sostenible de Colombia.": "Nuclear science at the service of Colombia's sustainable development.",
    "Síguenos en redes sociales": "Follow us on social media",
    "Verificación de Carné": "Card Verification",
    "Carné No Encontrado": "Card Not Found",
    "El enlace de verificación es inválido o el carné no existe en nuestro sistema.": "The verification link is invalid or the card does not exist in our system.",
    "Volver al Inicio": "Back to Home",
    "Carné Verificado": "Card Verified",
    "Miembro Fundador": "Founding Member",
    "Asociado ASNC": "ASNC Associate",
    "Emisión": "Issued",
    "Válido hasta": "Valid until",
    "Este carné ha sido verificado %(counter)s vez": "This card has been verified %(counter)s time",
    "Este carné ha sido verificado %(counter)s veces": "This card has been verified %(counter)s times",
    "Carné No Válido": "Invalid Card",
    "Carné Expirado": "Card Expired",
    "Este carné venció el %(fecha)s": "This card expired on %(fecha)s",
    "Carné Suspendido": "Card Suspended",
    "Carné Cancelado": "Card Cancelled",
    "Pendiente de Activación": "Pending Activation",
    "Si cree que esto es un error, contacte a": "If you believe this is an error, please contact",
    "¿Cómo puedes aportar a la ASNC?": "How can you contribute to the ASNC?",
    "¿Cómo puedes aportar a la ASNC? *": "How can you contribute to the ASNC? *",
})


# ---------------------------------------------------------------------------
# Extracción de msgid reales + compilación
# ---------------------------------------------------------------------------
def _norm(s):
    return re.sub(r'\s+', ' ', s).strip()


_LIT = r"(?:u?'(?:[^'\\]|\\.)*'|u?\"(?:[^\"\\]|\\.)*\")"
_RE_SINGLE = re.compile(r"(?<![A-Za-z_])gettext\(\s*(" + _LIT + r")\s*\)")
_RE_PLURAL = re.compile(r"(?<![A-Za-z_])ngettext\(\s*(" + _LIT + r")\s*,\s*(" + _LIT + r")\s*,")


def _extract(src):
    out = templatize(src)
    singles = [ast.literal_eval(m.group(1)) for m in _RE_SINGLE.finditer(out)]
    plurals = [(ast.literal_eval(m.group(1)), ast.literal_eval(m.group(2)))
               for m in _RE_PLURAL.finditer(out)]
    return singles, plurals


def _collect_msgids():
    """Extrae los msgid únicos (singulares y plurales) de todas las plantillas."""
    singles, plurals, seen = [], [], set()
    for rel in TEMPLATE_FILES:
        with open(os.path.join(BASE_DIR, rel), encoding='utf-8') as fh:
            s, p = _extract(fh.read())
        for m in s:
            if m not in seen:
                seen.add(m)
                singles.append(m)
        for pr in p:
            key = ('PL', pr[0], pr[1])
            if key not in seen:
                seen.add(key)
                plurals.append(pr)
    return singles, plurals


def _build_lang(lang, translations, singles, plurals):
    """Compila locale/<lang>/LC_MESSAGES/django.{po,mo}. Devuelve (n, faltantes)."""
    norm_map = {_norm(k): v for k, v in translations.items()}
    po = polib.POFile()
    po.metadata = {
        'Project-Id-Version': 'ASNC 1.0',
        'Report-Msgid-Bugs-To': 'info@asncol.com',
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Transfer-Encoding': '8bit',
        'Language': lang,
        'Plural-Forms': 'nplurals=2; plural=(n != 1);',
    }
    missing = []
    for msgid in singles:
        val = norm_map.get(_norm(msgid))
        if val is None:
            missing.append(msgid)
            continue
        po.append(polib.POEntry(msgid=msgid, msgstr=val))
    for sing, plur in plurals:
        v_s = norm_map.get(_norm(sing))
        v_p = norm_map.get(_norm(plur))
        if v_s is None or v_p is None:
            missing.append(sing)
            continue
        po.append(polib.POEntry(msgid=sing, msgid_plural=plur,
                                msgstr_plural={0: v_s, 1: v_p}))

    out_dir = os.path.join(BASE_DIR, 'locale', lang, 'LC_MESSAGES')
    os.makedirs(out_dir, exist_ok=True)
    po.save(os.path.join(out_dir, 'django.po'))
    po.save_as_mofile(os.path.join(out_dir, 'django.mo'))
    return len(po), missing


def build():
    # Idioma -> diccionario de traducciones. Español es el idioma fuente (msgid).
    langs = {'en': TRANSLATIONS}
    try:
        from translations_fr import TRANSLATIONS_FR
        langs['fr'] = TRANSLATIONS_FR
    except ImportError:
        print('AVISO: scripts/translations_fr.py no encontrado, se omite francés.')
    try:
        from translations_pt import TRANSLATIONS_PT
        langs['pt'] = TRANSLATIONS_PT
    except ImportError:
        print('AVISO: scripts/translations_pt.py no encontrado, se omite portugués.')

    singles, plurals = _collect_msgids()
    total = len(singles) + len(plurals)
    print(f'msgid extraídos de las plantillas: {total}\n')

    for lang, translations in langs.items():
        n, missing = _build_lang(lang, translations, singles, plurals)
        line = f'  {lang}: {n} entradas compiladas'
        if missing:
            line += f'  | SIN TRADUCIR: {len(missing)}'
        print(line)
        for m in missing[:15]:
            print(f'       - {m[:70]!r}')


if __name__ == '__main__':
    build()
