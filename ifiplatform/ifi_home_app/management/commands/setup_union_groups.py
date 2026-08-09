"""Rebuilds union_groups on both the nb "studentforeninger" page and its en
translation into: a row of two groups (Sentrale foreninger / Sittende
foreninger i Utvalget), then one standalone group (Andre foreninger),
creating any of the real UnionPage children that don't exist yet -- and,
for each, a matching en translation via wagtail_localize's own PO pipeline
(same mechanism seed_dev_data.py uses), since names here are proper nouns
and don't change between locales. Program-specific unions get their own
"Programspesifikke foreninger" section automatically, from UnionPage.
union_type alone (see StudentUnionCategoryPage.get_context()'s
program_unions) -- not curated here, and not part of union_groups at all.
Safe to re-run: unions are looked up by (parent, title, locale) before
creation, translations are looked up via has_translation() first, and each
locale's union_groups is only overwritten if the computed value differs
from what's already there (no duplicate pages, no spurious revisions).
Pass --cleanup once everything looks right on the site to delete the logo
source files under LOGO_DIR -- once uploaded, the database is the real
copy, so the files are only needed up to that point (see --cleanup's own
help text for exactly what it does and doesn't touch).
"""

from pathlib import Path

from django.conf import settings
from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from wagtail.coreutils import find_available_slug
from wagtail.images.models import Image
from wagtail.models import Locale
from wagtail_localize.models import Translation, TranslationSource

from ifi_home_app.models.article_models import StudentUnionCategoryPage, UnionPage

# Matches the slug core_views._get_localized_category already uses to find
# this same page ("studentforeninger", "nb") -- reused here instead of a
# hardcoded page id, since ids differ between local dev and production. The
# en translation is found via get_translation_or_none(), not a second
# hardcoded slug.
CATEGORY_SLUG = "studentforeninger"

# Bundled logo files, same convention as seed_dev_data.py's SEED_IMAGE_PATH
# (a top-level static/ dir, not an app-level one -- both resolve fine
# through {% static %}, but this is the one other management commands in
# this repo already read real files from at runtime).
LOGO_DIR = Path(settings.BASE_DIR) / "static" / "images" / "studentunions" / "logos"

# Fallback logo for unions with no real one found (currently just
# Fadderstyret) -- the site's own favicon, reused as a single shared Image
# rather than uploaded once per union.
DEFAULT_LOGO_PATH = Path(settings.BASE_DIR) / "ifi_home_app" / "static" / "images" / "favicon-512.png"
DEFAULT_LOGO_TITLE = "Default union logo (favicon)"

# title, union_type, purpose (nb/en), activities (nb/en, only where a
# distinct-from-purpose activity was actually documented somewhere -- never
# restated purpose text), website_url, email, social (list of (platform,
# url) pairs -- platform must be one of UnionPage.SOCIAL_PLATFORM_CHOICES),
# logo filename (in LOGO_DIR, or None to fall back to the site favicon if
# no official logo could be found). All sourced from mn.uio.no's org
# listing, ordenen.ifi.uio.no, foreninger.uio.no, or each union's own site
# -- not invented. Deliberately excludes sitting_members/member_count_*:
# those would mean publishing named individuals' contact info that goes
# stale every semester as boards turn over -- left for each union's own
# editors to fill in and keep current via Wagtail admin.
# Titles are proper nouns and stay identical in the en translation.
UNION_SPECS = [
    {
        # purpose_nb/activities_nb are the user's own hand-edit made
        # directly in Wagtail admin (2026-08-09), transcribed here verbatim
        # (data-block-key attrs stripped, meaningless outside the live
        # Draftail editor state) so the script stays in sync with reality.
        # purpose_en/activities_en are a direct translation of that text.
        "title": "dagen@ifi", "union_type": "general", "logo": "dagen.png",
        "website_url": "https://dagenatifi.no",
        "social": [
            ("instagram", "https://www.instagram.com/dagenatifi"),
            ("facebook", "https://www.facebook.com/dagenatifi"),
            ("linkedin", "https://www.linkedin.com/company/dagen-ifi"),
        ],
        "purpose_nb": "<p>Dagen@ifi består av både bachelor- og masterstudenter som jobber for å gi studenter muligheten til å møte bedrifter, og utforske de mange mulighetene de har i vente etter endt studie. Foreningen arrangerer årlig to karrieredager: Dagen@ifi om høsten og Ettermiddagen@ifi om våren.</p>",
        "purpose_en": "<p>Dagen@ifi consists of both bachelor's and master's students working to give students the opportunity to meet companies and explore the many opportunities awaiting them after their studies. The association holds two career days each year: Dagen@ifi in the fall and Ettermiddagen@ifi in the spring.</p>",
        "activities_nb": "<p>Dagen@ifi er en av de største IT-karrieredagene i Oslo. Her samles flere titalls bedrifter, og hundrevis av nysgjerrige IT-studenter fyller Ole-Johan Dahls hus.</p><p>Dagen@ifi er den perfekte muligheten for å bli kjent med bedrifter og jobbmulighetene de tilbyr, høre på spennende foredrag og knytte nye kontakter. Det blir store mengde pizza, merch, og gode muligheter for å lande drømmejobben.</p><p>Dagen avsluttes med underholdning, konsert, og en stor fest på kvelden!</p><p><b>I år blir Dagen@ifi holdt 4. September 2026.</b></p>",
        "activities_en": "<p>Dagen@ifi is one of the biggest IT career days in Oslo. Dozens of companies gather here, and hundreds of curious IT students fill Ole-Johan Dahls hus.</p><p>Dagen@ifi is the perfect opportunity to get to know companies and the job opportunities they offer, listen to exciting talks, and make new contacts. There's plenty of pizza, merch, and great chances to land your dream job.</p><p>The day wraps up with entertainment, a concert, and a big party in the evening!</p><p><b>This year, Dagen@ifi will be held on 4 September 2026.</b></p>",
    },
    {
        # ifinavet.no/organization blocks WebFetch/curl-with-default-headers
        # behind a Vercel bot challenge, but a plain curl with a real
        # browser UA got through once and revealed real embedded social
        # links (instagram/linkedin/github, fetched 2026-08-09) -- purpose/
        # activities sourced from 50.cyb.no's own Navet chapter (direct
        # Norwegian quotes) plus mn.uio.no.
        "title": "Navet", "union_type": "general", "logo": "navet.png",
        "website_url": "https://ifinavet.no",
        # ifinavet.no/info/vedtekter confirmed live (200), but the whole
        # site is a client-rendered Next.js/Clerk app -- the actual bylaws
        # text isn't in the static HTML anywhere, so only the link is
        # added here, no fabricated summary text.
        "vedtekter_url": "https://ifinavet.no/info/vedtekter",
        "social": [
            ("facebook", "https://www.facebook.com/ifi.navet/"),
            ("instagram", "https://www.instagram.com/ifinavet/"),
            ("linkedin", "https://www.linkedin.com/company/ifinavet/"),
            ("github", "https://github.com/ifinavet"),
        ],
        "purpose_nb": "Bedriftskontakten ved Institutt for informatikk ved Universitetet i Oslo. Fungerer som et sentralt møtepunkt mellom næringslivet og studentene, og skal gjøre det enkelt for bedrifter å komme i kontakt med studentene ved instituttet.",
        "purpose_en": "The business contact at the Department of Informatics, University of Oslo. Acts as a central meeting point between industry and students, making it easy for companies to get in touch with students at the department.",
        "activities_nb": "Tilbyr et sentralt kontakt- og koordineringspunkt for bedriftsrelaterte aktiviteter, praktisk hjelp med arrangementer (romreservasjon, markedsføring m.m.), oversikt over bedriftspresentasjoner og formidling av stillingsannonser. Gjennomfører 45-50 bedriftspresentasjoner årlig, stort sett tirsdager og torsdager gjennom skoleåret.",
        "activities_en": "Offers a central contact and coordination point for company-related activities, practical help with events (room booking, marketing, etc.), an overview of company presentations, and job listing postings. Runs 45-50 company presentations a year, mostly on Tuesdays and Thursdays throughout the school year.",
    },
    {
        # fu.png is FU's own touch-icon, pulled from fordelingsutvalget.org
        # itself (assets/img/touch-icon-192x192.png) -- not listed on
        # mn.uio.no's org page like the others, but a real FU asset. Purpose/
        # activities/vedtekter sourced from fordelingsutvalget.org/info/,
        # /vedtekter/ and /kontakt/ directly (fetched 2026-08-09).
        "title": "Fordelingsutvalget (FU)", "union_type": "general", "logo": "fu.png",
        "website_url": "https://fordelingsutvalget.org", "email": "fu-koordinator@ifi.uio.no",
        "purpose_nb": "Studentenes egen støtteordning ved Institutt for informatikk. Fordeler overskudd fra Navets og dagen@ifis arbeid til faglige og sosiale arrangementer for IFI-studenter -- helt uavhengig av UiO, SiO og lignende, og 100% finansiert av foreningene selv.",
        "purpose_en": "The students' own funding scheme at the Department of Informatics. Redistributes surplus from Navet's and dagen@ifi's work to academic and social events for IFI students -- entirely independent of UiO, SiO and similar, and 100% financed by the associations themselves.",
        "activities_nb": "Støtter blant annet den årlige Hemsedal-turen (100+ deltakere), Ifi-gallaen, fadderukas kveldsaktiviteter, og kurs som Git, Arduino og Emacs. Alle foreninger tilknyttet instituttet kan søke om midler.",
        "activities_en": "Supports things like the annual Hemsedal trip (100+ participants), the Ifi gala, fadderuke's evening activities, and courses like Git, Arduino and Emacs. Any association affiliated with the institute can apply for funds.",
        "vedtekter_nb": "Styres av et årlig allmøte i februar, foreningens øverste organ. Daglig drift ledes av en styringsgruppe med minst en koordinator og en sekretær (uten stemmerett). Elleve foreninger har stemmerett og må stille med minst én representant på møter. Utvalget kan årlig dele ut inntil 80% av foregående års overskudd fra Navet og dagen@ifi. Vanlige vedtak krever to tredjedels flertall blant representerte foreninger; vedtektsendringer krever tre firedels flertall på allmøtet.",
        "vedtekter_en": "Governed by an annual general assembly in February, the association's highest body. Day-to-day operations are run by a steering group with at least a coordinator and a secretary (non-voting). Eleven associations hold voting rights and must send at least one representative to meetings. The committee may distribute up to 80% of the previous year's surplus from Navet and dagen@ifi. Regular decisions require a two-thirds majority of represented associations; bylaw changes require a three-quarters majority at the general assembly.",
        "vedtekter_url": "https://fordelingsutvalget.org/vedtekter/",
    },
    {
        # cyb.no/aboutCYB itself is a client-rendered SPA (no server-side
        # HTML content to fetch) -- sourced instead from ordenen.ifi.uio.no's
        # own CYB page and corroborating WebSearch snippets (fetched
        # 2026-08-09).
        "title": "Cybernetisk Selskab", "union_type": "general", "logo": "cyb_peoply.png",
        "website_url": "https://cyb.no",
        # Instagram/Facebook/GitHub confirmed straight from cyb.no's own
        # footer (screenshotted by the user) -- Slack link shown there too,
        # but skipped: invite-gated internal chat, no public URL visible.
        "social": [
            ("instagram", "https://www.instagram.com/cybernetisk/"),
            ("facebook", "https://www.facebook.com/cybernetisk/"),
            ("github", "https://github.com/cybernetisk"),
        ],
        "purpose_nb": "En sosial, faglig og kulturell forening for alle studenter tilknyttet IFI. Bidrar til det sosiale og faglige miljøet ved instituttet, og driver studentkjelleren Escape.",
        "purpose_en": "A social, academic and cultural association for all students affiliated with IFI. Contributes to the social and academic environment at the institute, and runs the student basement bar Escape.",
        "activities_nb": "Arrangerer alt fra filmkvelder til skitur til Hemsedal. Hovedstyret (HS) har ansvar for arrangementer, rekruttering og økonomi, mens Kjellerstyret (KS) driver kjellerbaren Escape. Medlemmer får blant annet rabatterte priser på kafé og bar, egne medlemsfester, hyttetur og kurs.",
        "activities_en": "Organizes everything from film nights to a ski trip to Hemsedal. The Main Board (HS) handles events, recruitment and finances, while the Cellar Board (KS) runs the basement bar Escape. Members get discounted café/bar prices, exclusive member parties, a cabin trip, and courses.",
    },
    {
        # Sourced from defi.no, defi.no/om-oss and defi.no/vedtekter
        # directly (fetched 2026-08-09). Named board members intentionally
        # left out.
        "title": "Defi", "union_type": "program", "logo": "defi_peoply.png",
        "website_url": "https://defi.no", "email": "styret@defi.no",
        "vedtekter_url": "https://www.defi.no/vedtekter",
        "social": [
            ("instagram", "https://www.instagram.com/ifidefi/"),
            ("facebook", "https://www.facebook.com/DefiUiO"),
            ("linkedin", "https://www.linkedin.com/company/ifidefi/about/"),
        ],
        "purpose_nb": "Linjeforeningen for Informatikk: design, bruk og interaksjon ved UiO. Ivaretar designstudentenes interesser ved instituttet og driver linjerommet Euclid.",
        "purpose_en": "The line association for Informatics: Design, Use and Interaction at UiO. Represents design students' interests at the institute and runs the line's common room, Euclid.",
        "activities_nb": "Arrangerer prototyping- og metodeverksteder, sosiale aktiviteter som «Paint'n sip», t-skjortedesign-verksteder, foredrag (f.eks. sommerinternship som designer, CV-skriving), studentpub, linjefester og høytidelige feiringer.",
        "activities_en": "Runs prototyping and methodology workshops, social activities like a \"Paint'n sip\", t-shirt design workshops, talks (e.g. summer internships as a designer, CV writing), student pub nights, line parties and formal celebrations.",
        "vedtekter_nb": "Foreningen er politisk og religiøst nøytral, ikke-kommersiell og drives på frivillig basis. Generalforsamlingen er øverste organ, avholdes minst én gang i semesteret med minst to ukers varsel, og krever 6 fremmøtte for å være beslutningsdyktig. Vanlige vedtak krever simpelt flertall, vedtektsendringer krever 4/5 flertall. Styret har syv verv (leder, nestleder, økonomi-, PR- og arrangementsansvarlig, internansvarlig, ett styremedlem). Foreningen har egne varslingsrutiner (§13) for diskriminering, trakassering og mobbing. Oppløsning krever 9/10 flertall, bekreftet på et nytt møte tre måneder senere.",
        "vedtekter_en": "The association is politically and religiously neutral, non-commercial, and run on a voluntary basis. The general assembly is the highest body, held at least once a semester with at least two weeks' notice, and requires 6 attendees for quorum. Regular decisions require a simple majority; bylaw changes require a 4/5 majority. The board has seven positions (leader, deputy leader, finance/PR/events officers, internal affairs officer, one board member). The association has its own whistleblowing procedures (§13) for discrimination, harassment and bullying. Dissolution requires a 9/10 majority, confirmed at a second meeting three months later.",
    },
    {
        "title": "Digitus", "union_type": "program", "logo": "digitus.png",
        "website_url": "https://digitusuio.no", "email": "styret@digitusuio.no",
        # Bylaws live in a Google Doc (linked from digitusuio.no itself) --
        # only the chrome/header was fetchable, not the actual document
        # text, so only the link is added, no fabricated summary.
        "vedtekter_url": "https://docs.google.com/document/d/1KI4hprfkE0YeowlwM9CaJJ6z1wau988A1NWUfveGyj8/edit",
        "social": [
            ("facebook", "https://www.facebook.com/digitusuio/"),
            ("instagram", "https://www.instagram.com/digitus_uio/"),
            ("linkedin", "https://www.linkedin.com/company/digitusuio/"),
        ],
        "purpose_nb": "Linjeforeningen for studieprogrammet Informatikk: Digital Økonomi og Ledelse ved Universitetet i Oslo.",
        "purpose_en": "The line association for the program Informatics: Digital Economy and Management at the University of Oslo.",
        "activities_nb": "Arrangerer turer, fester, foredrag og formelle middager, åpne for både programstudenter og andre UiO-studenter.",
        "activities_en": "Organizes hiking trips, parties, lectures and formal dinners, open to both program students and other UiO students.",
    },
    {
        # ififui.no and /vedtekter/ fetched directly 2026-08-09.
        "title": "Fagutvalget ved Institutt for Informatikk (FUI)", "union_type": "general", "logo": "fui.png",
        "website_url": "https://ififui.no", "email": "fui@ififui.no",
        "vedtekter_url": "https://ififui.no/vedtekter/",
        "purpose_nb": "Informatikkstudentenes eget organ, og skal fungere som et bindeledd mellom studentene.",
        "purpose_en": "The informatics students' own body, acting as a link between the students.",
        "activities_nb": "Holder ukentlige møter og publiserer referater, drifter kurseevaluering og skapadministrasjon (bokskap), tar imot studenthenvendelser, og arrangerer sosiale og faglige aktiviteter som brettspillkvelder og kurs (f.eks. «Git Good»).",
        "activities_en": "Holds weekly meetings and publishes minutes, runs course evaluation and locker administration, takes student inquiries, and organizes social/academic activities like board game nights and courses (e.g. \"Git Good\").",
        "vedtekter_nb": "Skal ivareta studentenes faglige og sosiale forhold overfor instituttets ledelse og universitetet. Styret har 8-13 medlemmer og er beslutningsdyktig med minst halvparten til stede, ved simpelt flertall. Generalforsamlingen er øverste organ, krever minst 25 IFI-studenter for å være beslutningsdyktig, og holdes ved semesterstart. Medlemskap gjelder programstudenter ved IFI eller de som tar IN-emner. Vedtektsendringer krever 2/3 flertall, sanksjoner 2/3, oppløsning 3/4. Vervperiode er to semestre.",
        "vedtekter_en": "Safeguards students' academic and social interests with the institute's leadership and the university. The board has 8-13 members and reaches quorum with at least half present, deciding by simple majority. The general assembly is the highest body, requires at least 25 IFI students for quorum, and is held at the start of each semester. Membership covers program students at IFI or those taking IN-prefixed courses. Bylaw changes require a 2/3 majority, sanctions 2/3, dissolution 3/4. Terms last two semesters.",
    },
    {
        "title": "Mikro", "union_type": "program", "logo": "mikro.png",
        "website_url": "https://foreninger.uio.no/mikro/", "email": "mikro-styret@ifi.uio.no",
        # facebook/instagram confirmed straight from foreninger.uio.no/mikro/
        # itself (more authoritative than the older ordenen.ifi.uio.no link).
        "social": [
            ("facebook", "https://www.facebook.com/ifiMikro"),
            ("instagram", "https://www.instagram.com/ifimikro/"),
        ],
        "purpose_nb": "Studentforeningen for studenter tilknyttet Nanoelektronikk, Robotikk og Digital Signalbehandling.",
        "purpose_en": "The student association for students affiliated with Nanoelectronics, Robotics and Digital Signal Processing.",
        "activities_nb": "Arrangerer fagkvelder hvor masterstudenter, forelesere og professorer i nanoelektronikk, robotikk og digital signalbehandling deler forskning og karriereinnsikt, samt Mikros konstruksjonslaug -- et utvalg for prosjekter innenfor robotikk og elektronikk.",
        "activities_en": "Holds professional evenings where master's students, lecturers and professors in nanoelectronics, robotics and digital signal processing share research and career insight, plus Mikro's construction guild -- a committee for projects within robotics and electronics.",
        # Full text read directly from the bylaws PDF (fetched 2026-08-09).
        "vedtekter_url": "https://foreninger.uio.no/mikro/om/Vedtekter/gjeldende_vedtekter_08.02.2018.pdf",
        "vedtekter_nb": "Formålet er å fremme det sosiale miljøet blant medlemmene, og orientere dem om faglig relevante foredrag, ekskursjoner og annen virksomhet. Medlemmer er studenter på bachelorprogrammene «Informatikk: Robotikk og Intelligente Systemer»/«Nanoelektronikk og Robotikk», eller tilhørende masterprogram. Ingen medlemskontingent. Styret har 6-8 medlemmer (leder, nestleder og kasserer er faste verv). Generalforsamlingen er høyeste myndighet, beslutningsdyktig med minst 10 medlemmer til stede, avholdes ved høstsemesterets start. Vedtektsendringer krever 2/3 flertall. Oppløsning krever 2/3 flertall på to påfølgende generalforsamlinger; midler tilfaller Fordelingsutvalget (FU).",
        "vedtekter_en": "The purpose is to foster the social environment among members and inform them of academically relevant talks, excursions and other activities. Membership covers students on the \"Informatics: Robotics and Intelligent Systems\"/\"Nanoelectronics and Robotics\" bachelor's programs, or related master's programs. No membership fee. The board has 6-8 members (leader, deputy leader and treasurer are fixed roles). The general assembly is the highest authority, reaching quorum with at least 10 members present, held at the start of the fall semester. Bylaw changes require a 2/3 majority. Dissolution requires a 2/3 majority at two consecutive general assemblies; funds go to Fordelingsutvalget (FU).",
    },
    {
        # Renamed from "Linjeforening for Språkteknologi" on 2025-06-06 --
        # now covers both programs (ordenen.ifi.uio.no/association/maki/).
        # purpose_nb/activities_nb are the user's own hand-edit made
        # directly in Wagtail admin (2026-08-09), transcribed here verbatim
        # (data-block-key attrs stripped, meaningless outside the live
        # Draftail editor state) so the script stays in sync with reality.
        # purpose_en/activities_en are a direct translation of that text.
        "title": "MA:KI", "union_type": "program", "logo": "maki.png",
        "social": [("facebook", "https://facebook.com/IFIMAKI")],
        "purpose_nb": "<p>MA:KI er linjeforeningen for maskinlæring og kunstig intelligens og språkteknologi, på både batchelor og master nivå.<br/></p><p>Foreningen hadde tidligere navnet LI:ST og fikk sitt nye navn i 2025 da studiet maskinlæring og kunstig intelligens erstattet studiet for språkteknologi.</p><p>Formålet med linjeforeningen er å lage muligheter for studenter å dele og styrke faglig kompetanse, samt gi muligheter for å skape et godt sosialt miljø.</p>",
        "purpose_en": "<p>MA:KI is the line association for machine learning and artificial intelligence and language technology, at both bachelor's and master's level.<br/></p><p>The association was previously named LI:ST and got its new name in 2025 when the machine learning and artificial intelligence program replaced the language technology program.</p><p>The purpose of the line association is to create opportunities for students to share and strengthen academic competence, as well as opportunities to build a good social environment.</p>",
        "activities_nb": "<p>Aktiviteter er innebærer fagkvelder, sosiale aktiviteter og generalforsamling.</p>",
        "activities_en": "<p>Activities include academic evenings, social activities and a general assembly.</p>",
    },
    {
        "title": "MAPS", "union_type": "general", "logo": "maps.png",
        "website_url": "https://foreninger.uio.no/maps/", "email": "maps-kontakt@studorg.uio.no",
        "social": [("github", "https://github.com/mapsuio")],
        "purpose_nb": "Foreningen for IFI-studenter som liker programmering og matematikk.",
        "purpose_en": "The association for IFI students who enjoy programming and mathematics.",
        "activities_nb": "Arrangerer NM i programmering, «Prog og Påfyll»-konkurranser, lyntaler og foredrag om teoretisk informatikk.",
        "activities_en": "Organizes the Norwegian programming championship, \"Prog og Påfyll\" algorithm competitions, lightning talks and talks on theoretical computer science.",
        # Full text read directly from the bylaws PDF (fetched 2026-08-09).
        "vedtekter_url": "https://foreninger.uio.no/maps/om/vedtekter/vedtekter.pdf",
        "vedtekter_nb": "Formålet er å fremme interesse for programmering og matematikk og samspillet mellom dem, og skape gode muligheter for faglig og sosial utfoldelse blant studentene. Medlemskap krever betalt kontingent. Generalforsamlingen er høyeste organ, holdes årlig innen utgangen av september med minst 14 dagers varsel, vedtak fattes ved simpelt flertall (2/3 for vedtektsendringer). Styret har 3-8 medlemmer, valgt for én periode. Økonomiansvarlig representerer MAPS i Fordelingsutvalget. Oppløsning krever 2/3 flertall på to påfølgende generalforsamlinger.",
        "vedtekter_en": "The purpose is to promote interest in programming and mathematics and the interplay between them, and to create good opportunities for academic and social development among students. Membership requires a paid fee. The general assembly is the highest body, held annually by the end of September with at least 14 days' notice, deciding by simple majority (2/3 for bylaw changes). The board has 3-8 members, elected for one term. The finance officer represents MAPS on Fordelingsutvalget. Dissolution requires a 2/3 majority at two consecutive general assemblies.",
    },
    {
        "title": "ProgSys", "union_type": "program", "logo": "progsys_peoply.png",
        "website_url": "https://progsys.no",
        "social": [
            ("facebook", "https://www.facebook.com/ifiprogsys/"),
            ("instagram", "https://www.instagram.com/ifiprogsys/"),
            ("discord", "https://discord.com/invite/Ng5J8xrrtu"),
            ("github", "https://github.com/IFI-Prog-Sys"),
        ],
        # Bylaws sourced from github.com/IFI-Prog-Sys/vedtekter directly
        # (fetched 2026-08-09) -- progsys.no itself is a client-rendered
        # SPA with no server-side page text to scrape beyond its tagline.
        "vedtekter_url": "https://github.com/IFI-Prog-Sys/vedtekter",
        "purpose_nb": "Linjeforeningen for Informatikk: programmering og systemarkitektur. Fremmer det sosiale og faglige miljøet på master- og bachelorprogrammet.",
        "purpose_en": "The line association for Informatics: Programming and System Architecture. Promotes the social and academic environment on the master's and bachelor's program.",
        "activities_nb": "Arrangerer faglig relevante og sosiale arrangementer, og jobber for et godt miljø i programrommet. Motto: «Making IFI fun, one event at a time».",
        "activities_en": "Organizes academically relevant and social events, and works to keep the program room a good place to be. Motto: «Making IFI fun, one event at a time».",
        "vedtekter_nb": "Styres av en generalforsamling som møtes høst og vår (innen utgangen av oktober og februar), og krever minst 10 stemmeberettigede til stede. Vanlige vedtak krever simpelt flertall, vedtektsendringer krever to tredjedels flertall. Styret består av 5-11 medlemmer valgt årlig, med leder, nestleder, økonomiansvarlig og teknisk ansvarlig som faste roller. Ved oppløsning kreves to tredjedels flertall på to påfølgende generalforsamlinger, og midler overføres til Fordelingsutvalget.",
        "vedtekter_en": "Governed by a general assembly meeting in fall and spring (by end of October and February respectively), requiring at least 10 voting members present. Regular decisions require a simple majority; bylaw changes require a two-thirds majority. The board has 5-11 members elected annually, with Chair, Vice-Chair, Finance Officer and Technical Officer as fixed roles. Dissolution requires a two-thirds majority at two consecutive general assemblies, with assets transferred to Fordelingsutvalget.",
    },
    {
        "title": "Sifi", "union_type": "general", "logo": "sifi.jpg",
        "website_url": "https://sifi.no", "email": "sikkerhet@ifi.uio.no",
        "social": [
            ("instagram", "https://www.instagram.com/sikkerhetifi/"),
            ("linkedin", "https://www.linkedin.com/company/sikkerhetifi/"),
            ("facebook", "https://www.facebook.com/profile.php?id=100091625065665"),
        ],
        "purpose_nb": "Sikkerhet på IFI (Sifi) er linjeforeningen for Informasjonssikkerhet ved UiO. Alle studenter på masterprogrammet blir automatisk medlemmer. Holder sosiale og faglige arrangementer for å skape et godt miljø for medlemmer og andre interesserte studenter ved instituttet.",
        "purpose_en": "Sikkerhet på IFI (Sifi) is the line association for Information Security at UiO. All students on the master's program automatically become members. Holds social and academic events to create a good environment for members and other interested students at the institute.",
    },
    {
        # fadderstyret.png rasterized from foreninger.uio.no's own SVG
        # asset (decorating/images/fadder_ifi_logo.svg) via resvg-py, then
        # cropped to just the icon mark (the source is a wide wordmark+icon
        # lockup, which crops badly against the circular card frame).
        "title": "Fadderstyret", "union_type": "general", "logo": "fadderstyret.png",
        "website_url": "https://foreninger.uio.no/fadderuke-ifi/", "email": "fadderstyret@ifi.uio.no",
        "social": [("instagram", "https://www.instagram.com/fadderukeifi/")],
        "purpose_nb": "Rekrutterer faddere ved IFI og legger til rette for en sosial studiestartuke for de nye bachelorkullene.",
        "purpose_en": "Recruits mentors at IFI and organizes a social orientation week for new bachelor cohorts.",
    },
    {
        "title": "FIFI", "union_type": "general", "logo": "fifi.png",
        "email": "kontakt@fotballvedifi.no",
        "social": [("instagram", "https://www.instagram.com/fifivedifi/")],
        "purpose_nb": "En sosial og sportslig forening ved instituttet.",
        "purpose_en": "A social and sports association at the institute.",
        "activities_nb": "Holder ukentlige treninger på Domus Athletica gjennom semesteret, samt faste arrangementer på instituttet med fokus på fotball.",
        "activities_en": "Holds weekly training sessions at Domus Athletica throughout the semester, plus regular football-focused events at the institute.",
    },
    {
        # fordelingsutvalget.org/foreninger/ lists this as inactive.
        "title": "IF1", "union_type": "general", "logo": "if1.jpeg", "status": "retired",
        "email": "styret@if1.no",
        "social": [("facebook", "https://www.facebook.com/instituttf1")],
        "purpose_nb": "En forening for Formel 1-interesserte. Foreningen arrangerer blant annet visninger av Formel 1-løp.",
        "purpose_en": "An association for Formula 1 enthusiasts. Among other things, the association organizes screenings of Formula 1 races.",
    },
    {
        "title": "IFI-Avis", "union_type": "general", "logo": "ifiavis.png",
        "website_url": "https://ifiavis.no",
        "social": [
            ("facebook", "https://www.facebook.com/outputifi"),
            ("instagram", "https://www.instagram.com/outputifi/"),
        ],
        "purpose_nb": "Foreningen bak magasinet Output, som gis ut én gang i semesteret ved Institutt for Informatikk.",
        "purpose_en": "The association behind the Output magazine, published once a semester at the Department of Informatics.",
        "activities_nb": "Skriving, fotografering, illustrasjon, design, sosiale sammenkomster, møter og redaksjonelt arbeid.",
        "activities_en": "Writing, photography, illustration, design, social gatherings, meetings and editorial work.",
        "vedtekter_url": "https://www.ifiavis.no/vedtekter",
        "vedtekter_nb": "Styres av tre organ: Generalforsamlingen (høyeste myndighet), Styret (leder, nestleder, økonomi- og PR-ansvarlig, samt et styremedlem) og Redaksjonen (redaktør, assisterende redaktør, designansvarlig, foto/illustrasjonsansvarlig, korrekturleser). Stemmerett har alle IFI-studenter. Minst 2/3 av styret må være IFI-studenter. Vedtektsendringer krever 2/3 flertall; styret er beslutningsdyktig med 2/3 fremmøte, og leders stemme teller dobbelt ved stemmelikhet.",
        "vedtekter_en": "Governed by three bodies: the General Assembly (highest authority), the Board (leader, deputy leader, finance and PR officers, plus one board member), and the Editorial Team (editor, co-editor, design officer, photo/illustration officer, proofreader). All IFI students have voting rights. At least 2/3 of the board must be IFI students. Bylaw changes require a 2/3 majority; the board reaches quorum with 2/3 attendance, and the leader's vote counts double in ties.",
    },
    {
        # fordelingsutvalget.org/foreninger/ confirms this is inactive
        # (listed as "IFIPDL" there).
        "title": "ifiPDL", "union_type": "general", "logo": "ifipdl.png", "status": "retired",
        "purpose_nb": "En forening for spreke og padel-interesserte!",
        "purpose_en": "An association for active people and padel enthusiasts!",
    },
    {
        # ordenen.ifi.uio.no is clear this is IFI's literary association,
        # not just a generic social club (its own earlier one-line blurb
        # elsewhere undersold this) -- ifireadline.web.app confirmed live.
        # logo swapped to readLine's own peoply.app/orgs/readline icon (a
        # hand-drawn "readLine" wordmark, pulled from peoply's blob storage,
        # not the generic Pooh-with-a-book image mn.uio.no had) per explicit
        # user preference.
        "title": "readLine", "union_type": "general", "logo": "readline_peoply.jpg",
        "website_url": "https://ifireadline.web.app",
        # Real signup form, confirmed by its own title ("Du vil være med i
        # readLine?") when fetched 2026-08-09.
        "signup_url": "https://docs.google.com/forms/d/e/1FAIpQLSeVwrbP4Vdfhtzx9djqNg2Qy91_w-ruoYCcaKmDJBpSFjJaQw/viewform",
        "purpose_nb": "IFIs litterære forening, tolket i sin videste forstand.",
        "purpose_en": "IFI's literary association, interpreted in the broadest sense.",
    },
    {
        "title": "VIFI", "union_type": "general", "logo": "vifi.png",
        "social": [("facebook", "https://www.facebook.com/VIFI-112592593608578/")],
        "purpose_nb": "Foreningen for volleyballglade studenter.",
        "purpose_en": "The association for volleyball-loving students.",
        "activities_nb": "Medlemmene spiller volleyball sammen halvannen time i uken på Athletica.",
        "activities_en": "Members play volleyball together for one and a half hours a week at Athletica.",
    },
    # The following 6 were missing from the original pass -- found via
    # ordenen.ifi.uio.no's own "Active Associations" list (IFI-Logen,
    # RealitIFI, Ifi Sjakk, Toastjærn) and independent web search/peoply
    # (Rastløs, Quizifi), fetched 2026-08-09.
    {
        # Confirmed dead by the user directly, and by
        # fordelingsutvalget.org/foreninger/ (listed as "Ifi-logen" there).
        "title": "IFI-Logen", "union_type": "general", "logo": "ifi-logen.jpg", "status": "retired",
        "social": [("facebook", "https://www.facebook.com/ifilogen")],
        "purpose_nb": "En sosial studentorganisasjon ved IFI, kjent for sitt (skjemtsomme) mål om å skaffe instituttet en jacuzzi.",
        "purpose_en": "A social student organization at IFI, known for its (tongue-in-cheek) goal of getting the department a jacuzzi.",
    },
    {
        # fordelingsutvalget.org/foreninger/ lists this as active, resolving
        # the earlier "unknown" uncertainty (no other site/social existed).
        "title": "RealitIFI", "union_type": "general", "logo": "realitifi.jpg",
        "purpose_nb": "Møtes hver uke kl. 08:15 for å se en utvalgt realityserie sammen -- et sosialt påskudd for å komme seg tidlig opp. Ny serie velges hvert semester. Grunnlagt 25. januar 2023.",
        "purpose_en": "Meets every week at 08:15 to watch a chosen reality series together -- a social excuse to get up early. A new series is picked each semester. Founded 25 January 2023.",
    },
    {
        # fordelingsutvalget.org/foreninger/ lists this as inactive.
        "title": "Ifi Sjakk", "union_type": "general", "logo": "ifi-sjakk.jpg", "status": "retired",
        "social": [("facebook", "https://www.facebook.com/ifisjakk/")],
        "purpose_nb": "En interesseforening for sjakkinteresserte studenter ved Institutt for informatikk, med faste sjakkarrangementer. Grunnlagt 2015.",
        "purpose_en": "An interest association for chess-loving students at the Department of Informatics, with regular chess events. Founded 2015.",
    },
    {
        # Its foreninger.uio.no/toastjaern/ link 404s and no other working
        # link was found, but confirmed genuinely active by the user
        # directly.
        "title": "Toastjærn", "union_type": "general", "logo": "toastjaern.png",
        "purpose_nb": "Sprer glede rundt toasting, og skaper samhold og tilhørighet i studentmiljøet.",
        "purpose_en": "Spreads joy around toasting, and builds fellowship and belonging in the student community.",
    },
    {
        # ifirastlos.no doesn't resolve (DNS) -- Instagram used instead as
        # the real, verified link. Logo reused from a pre-existing asset
        # already in this repo (static/images/studentunions/
        # IFIRastløsLogo.jpg, present before this session).
        "title": "Rastløs", "union_type": "general", "logo": "rastlos_peoply.png",
        "social": [("instagram", "https://www.instagram.com/ifirastlos/")],
        "purpose_nb": "Fremmer fysisk aktivitet og fellesskap blant IFI-studenter på tvers av studieretninger -- fra små skogsturer til større turer som Besseggen. Lavterskeltilbud åpent for alle IFI-tilknyttede studenter.",
        "purpose_en": "Promotes physical activity and community among IFI students across study programs -- from short forest walks to bigger trips like Besseggen. A low-threshold offering open to all IFI-affiliated students.",
    },
    {
        "title": "Quizifi", "union_type": "general", "logo": "quizifi.jpg",
        "social": [("instagram", "https://www.instagram.com/quizifi/")],
        "purpose_nb": "En sosial forening som arrangerer quizkvelder og andre morsomme arrangementer for alle studenter ved Institutt for informatikk.",
        "purpose_en": "A social association that organizes quiz nights and other fun events for all students at the Department of Informatics.",
    },
    # Found via peoply.app/orgs' own sitemap.xml (the org listing itself is
    # a client-rendered page with no server-side content, but its sitemap
    # lists every org slug directly) -- fetched 2026-08-09.
    {
        # Its own peoply.app/orgs/pgaifi page confirms it's real (description
        # + logo pulled straight from there), so kept as active even though
        # its Spond invite link (spond.com/invite/CBDAX) 404s -- dropped
        # that link rather than pointing at something broken.
        "title": "PGA IFI", "union_type": "general", "logo": "pgaifi.jpg",
        "purpose_nb": "IFI sin helt egne golfforening.",
        "purpose_en": "IFI's very own golf association.",
    },
    {
        "title": "PiTCH", "union_type": "program", "logo": "pitch.png",
        "purpose_nb": "Programforeningen for masterprogrammet Entreprenørskap og innovasjonsledelse ved IFI.",
        "purpose_en": "The program association for the master's program Entrepreneurship and Innovation Leadership at IFI.",
    },
    {
        "title": "Runtime", "union_type": "general", "logo": "runtime.png",
        "purpose_nb": "IFI-studentenes løpeforening. Driver hovedsakelig med løping, inkludert langdistanse og intervalltrening, med sykkelturer om sommeren.",
        "purpose_en": "The IFI students' running association. Mainly focused on running, including long-distance and interval training, with bike rides in summer.",
    },
    {
        # The user's own club, also on peoply -- description/icon straight
        # from peoply.app/orgs/ifipitbulls.
        "title": "Ifi Pitbulls", "union_type": "general", "logo": "pitbulls.jpg", "show_in_menu": True,
        "purpose_nb": "Inspirert av artisten Pitbull. Kler seg som Pitbull, bryter isen og skaper fest og god stemning.",
        "purpose_en": "Inspired by the artist Pitbull. Dresses up as Pitbull, breaks the ice and creates a party atmosphere.",
    },
    {
        # The user's own guild -- not found on peoply or anywhere public.
        # Logo reused from a pre-existing asset already in this repo
        # (static/images/studentunions/IfiGuildOfCreatorsLogo.png, present
        # before this session). No purpose text -- left for the user to
        # fill in themselves via Wagtail admin, not guessed at.
        "title": "Ifi-Creators' Guild", "union_type": "general", "logo": "creators-guild.png", "show_in_menu": True,
        "purpose_nb": "", "purpose_en": "",
    },
]

# The three central organizations.
SENTRALE = ["dagen@ifi", "Navet", "Fordelingsutvalget (FU)"]

# The 11 voting members of Utvalget, per IFI's own "Hvem sitter i utvalget?"
# page. dagen@ifi/Navet deliberately also sit in SENTRALE above -- a union
# can belong to more than one group, union_groups is additive by design.
UTVALGET = [
    "dagen@ifi",
    "Navet",
    "Cybernetisk Selskab",
    "Defi",
    "Digitus",
    "Fagutvalget ved Institutt for Informatikk (FUI)",
    "Mikro",
    "MA:KI",
    "MAPS",
    "ProgSys",
    "Sifi",
]

# (nb title, en title, member titles) -- the two groups shown side by side
# in the row. This is the only curated grouping left in union_groups --
# "Programspesifikke foreninger" and "Andre foreninger" are both fully
# automatic now (see StudentUnionCategoryPage.get_context()'s
# program_unions/other_unions and studentunion_category_page.html):
# program_unions is every union_type="program" union, and other_unions is
# every active union not already in Sentrale/Utvalget above and not
# program-specific -- the true leftover bucket, computed by exclusion so a
# union can never end up listed there *and* in its own more specific
# section (that duplication is what a hand-maintained ANDRE list used to
# risk, e.g. PiTCH showing up in both).
ROW_GROUP_SPECS = [
    ("Sentrale foreninger", "Central organizations", SENTRALE),
    ("Sittende foreninger i Utvalget", "Members of Utvalget", UTVALGET),
]

# No more standalone groups are curated here -- kept as an empty list (not
# deleted outright) since _build_union_groups_value() below still supports
# appending standalone "group" blocks, in case a genuinely new curated
# grouping (something no field/exclusion logic could express) comes up
# later.
STANDALONE_GROUP_SPECS = []

# Real, no-longer-active IFI unions, per ordenen.ifi.uio.no/association/'s
# own "Previous/Inactive Associations" list (fetched 2026-08-09). Not part
# of any union_groups entry -- these only ever show up in the "Old, but
# not forgotten" section (StudentUnionCategoryPage.get_context()'s
# retired_unions), via UnionPage.status="retired". logo is each union's own
# real logo image pulled directly from its ordenen.ifi.uio.no page (marked
# alt="Logo for ..." there, as opposed to "Cover Image for <person>" --
# those are individual members' photos, deliberately not used) -- None
# where no logo was ever posted, which falls back to the site favicon via
# _get_or_create_logo() same as any active union without one. No socials/
# emails chased for these (mostly dead
# links, not worth it for historical records). Where one union renamed
# into/became another, that's noted in its purpose text rather than
# silently dropped.
RETIRED_UNION_SPECS = [
    {
        "title": "Applitude", "logo": None,
        "purpose_nb": "Skapte og vedlikeholdt et godt sosialt og faglig miljø for mobil apputvikling blant studenter ved UiO, med kurs, sosiale arrangementer og faste programmeringskvelder.",
        "purpose_en": "Created and maintained a good social and academic environment for mobile app development among UiO students, with courses, social events and regular programming evenings.",
    },
    {
        "title": "Ifi Rotor", "logo": "ifi-rotor.jpg",
        "purpose_nb": "Studentforening for RC-multikopter-bygging og flyvning, med verksteder og foredrag for å bygge kunnskap og miljø rundt hobbyen.",
        "purpose_en": "A student association for RC multicopter building and flying, with workshops and talks to build knowledge and community around the hobby.",
    },
    {
        # Successor of IT-SLP (renamed 2010), later became LI:ST (2017),
        # which in turn became today's active MA:KI (2025) -- a four-name
        # lineage across nearly two decades.
        "title": "PI:SK (Programutvalget for Informatikk: språk og kommunikasjon)", "logo": None,
        "purpose_nb": "Jobbet for et bra faglig og sosialt miljø rundt studieprogrammet, med fagkvelder og allmøter. Tidligere IT-SLP (til 2010); ble videreført som LI:ST i 2017, som senere ble til dagens MA:KI i 2025.",
        "purpose_en": "Worked for a good academic and social environment around the study program, with academic evenings and general assemblies. Formerly IT-SLP (until 2010); carried on as LI:ST in 2017, which later became today's MA:KI in 2025.",
    },
    {
        "title": "Svett", "logo": "svett.png",
        "purpose_nb": "Fremmet studenters interesse for spesielle informatiske fagområder gjennom foredrag, verksteder og konkurranser. Etablert 2015, avviklet 2017.",
        "purpose_en": "Promoted students' interest in specialized computer science topics through talks, workshops and competitions. Founded 2015, dissolved 2017.",
    },
    {
        "title": "Åpen sone for eksperimentell informatikk", "logo": "sonen.jpg",
        "purpose_nb": "Et studentlaboratorium ved instituttet -- et prosjektbasert møtested for engasjerte og nysgjerrige studenter.",
        "purpose_en": "A student laboratory at the institute -- a project-based meeting place for engaged and curious students.",
    },
    {
        "title": "Appsolutt", "logo": "appsolutt.jpg",
        "purpose_nb": "En studentforening i Oslo for alle interesserte i frontend-utvikling, med kurs, sosiale samlinger og faste programmeringstreff.",
        "purpose_en": "A student association in Oslo for anyone interested in frontend development, with courses, social gatherings and regular programming meetups.",
    },
    {
        "title": "IFI-Spillutvikling", "logo": "ifi-spillutvikling.png",
        "purpose_nb": "Fremmet spillutviklingsinteressen blant studentene som møtested for kunnskapsdeling og samarbeidsprosjekter. Grunnlagt 2018.",
        "purpose_en": "Promoted interest in game development among students as a meeting place for knowledge-sharing and collaborative projects. Founded 2018.",
    },
    {
        "title": "PING", "logo": None,
        "purpose_nb": "Etablerte og opprettholdt et faglig og sosialt miljø rundt fagområdene informasjons- og kommunikasjonsteknologi. Opprettet 10. september 1997.",
        "purpose_en": "Established and maintained an academic and social environment around information and communication technology. Founded 10 September 1997.",
    },
    {
        "title": "TekNat", "logo": "teknat.jpg",
        "purpose_nb": "En forening for realfag- og matematikkinteresserte, som bidro til et faglig og sosialt miljø for informatikkstudenter.",
        "purpose_en": "An association for students interested in mathematics and natural sciences, contributing to an academic and social environment for informatics students.",
    },
    {
        "title": "Homebrew", "logo": "homebrew.jpg",
        "purpose_nb": "Fremmet interesse for og kunnskap om øl- og vinbrygging blant IFI-studenter, med bryggeaktiviteter for medlemmer og styret. Opprettet 21. mars 2017.",
        "purpose_en": "Promoted interest in and knowledge of beer and wine brewing among IFI students, with brewing activities for members and the board. Founded 21 March 2017.",
    },
    {
        # Renamed to PI:SK in 2010 -- see that entry's own lineage note.
        "title": "IT-SLP (Programutvalget for IT: Språk, Logikk og Psykologi)", "logo": None,
        "purpose_nb": "Arrangerte sosiale aktiviteter og var bindeledd mellom studentene og programmets ledelse. Ble til Programutvalget for Informatikk: språk og kommunikasjon (PI:SK) i 2010.",
        "purpose_en": "Organized social activities and served as a link between students and the program's leadership. Became Programutvalget for Informatikk: språk og kommunikasjon (PI:SK) in 2010.",
    },
    {
        # Became today's active ProgSys on 2018-02-23.
        "title": "ProgNett", "logo": None,
        "purpose_nb": "Fremmet det sosiale og faglige miljøet ved bachelor- og masterprogrammene Programmering og nettverk. Ble til ProgSys 23. februar 2018.",
        "purpose_en": "Promoted the social and academic environment on the Programming and Networks bachelor's and master's programs. Became ProgSys on 23 February 2018.",
    },
    {
        "title": "UniPlay", "logo": "uniplay.png",
        "purpose_nb": "Etablerte og opprettholdt det sosiale miljøet for foreningens medlemmer, som vertskap for spillservere og aktiviteter. Grunnlagt 2014.",
        "purpose_en": "Established and maintained the social environment for the association's members, hosting game servers and activities. Founded 2014.",
    },
    {
        "title": "Ifi Makers", "logo": "ifi-makers.png",
        "purpose_nb": "Opprettholdt et godt sosialt miljø for studenter og eksterne engasjert i Åpen sone, med turer og treff. Grunnlagt 2016.",
        "purpose_en": "Maintained a good social environment for students and outsiders engaged in Åpen sone, with trips and meetups. Founded 2016.",
    },
    {
        # Continuation of PI:SK/IT-SLP; became today's active MA:KI on
        # 2025-06-06 -- see PI:SK's entry for the fuller lineage.
        "title": "LI:ST (Linjeforening for Språkteknologi)", "logo": "list.png",
        "purpose_nb": "Jobbet for et bra faglig og sosialt miljø rundt studieprogrammet Informatikk: Språkteknologi, gjennom fagkvelder, sosiale aktiviteter og allmøter. En videreføring av PI:SK/IT-SLP. Ble til MA:KI 6. juni 2025.",
        "purpose_en": "Worked for a good academic and social environment around the Informatics: Language Technology program, through academic evenings, social activities and general assemblies. A continuation of PI:SK/IT-SLP. Became MA:KI on 6 June 2025.",
    },
    {
        "title": "ProsIT (Linjeforeningen Profesjonsstudentene ved Institutt for Informatikk)", "logo": None,
        "purpose_nb": "Den sosiale foreningen for profesjonsstudentene ved instituttet, med sosiale arrangementer, bedriftsbesøk og den årlige Hemsedalturen. Inaktiv siden 2009.",
        "purpose_en": "The social association for professional-degree students at the institute, with social events, company visits and the annual Hemsedal trip. Inactive since 2009.",
    },
    {
        "title": "Jenteforeningen Verdande", "logo": "verdande.jpg",
        "purpose_nb": "Jenteforeningen ved instituttet. Formålet er å knytte bånd mellom jenter på instituttet og andre kvinner og jenter interessert i informatikk, med workshops, filmkvelder og grilling.",
        "purpose_en": "The institute's association for girls/women. Its purpose is to build ties between girls at the institute and other women and girls interested in informatics, with workshops, film nights and barbecues.",
    },
    # The following 7 are all listed as inactive on
    # fordelingsutvalget.org/foreninger/ itself (fetched 2026-08-09) --
    # not on ordenen.ifi.uio.no's own index, so likely newer/shorter-lived
    # associations than that list covers.
    {
        "title": "BrewFI", "logo": None,
        "purpose_nb": "En bryggeforening ved IFI, viet til øl- og vinbrygging blant studentene.",
        "purpose_en": "A brewing association at IFI, dedicated to beer and wine brewing among students.",
    },
    {
        # UiO Frisbeegolf -- DUKK, org.nr. 919 517 387, established
        # 2017-08-28 (foreninger.uio.no/dukk/).
        "title": "DUKK (UiO Frisbeegolf)", "logo": "dukk.png",
        "purpose_nb": "En frivillig studentforening ved UiO som vil formidle gleden ved frisbeegolf til studenter, uansett ferdighetsnivå. Arrangerte introduksjoner, miniturneringer og puttekonkurranser. Stiftet 28. august 2017.",
        "purpose_en": "A voluntary student association at UiO that wanted to spread the joy of disc golf to students, regardless of skill level. Organized introductions, mini-tournaments and putting competitions. Founded 28 August 2017.",
    },
    {
        "title": "IFI-fokus", "logo": None,
        "purpose_nb": "Arrangerte felles pomodoro-baserte studieøkter og studiegrupper for IFI-studenter.",
        "purpose_en": "Organized shared pomodoro-based study sessions and study groups for IFI students.",
    },
    {
        "title": "IFI-Podcast", "logo": None,
        "purpose_nb": "En podkast laget av seks IFI-studenter for å underholde medstudenter i studiehverdagen.",
        "purpose_en": "A podcast made by six IFI students to entertain fellow students during the study week.",
    },
    {
        "title": "iFriluft", "logo": None,
        "purpose_nb": "Fremmet fysisk aktivitet og friluftsliv blant IFI-studenter, fra små turer i marka til større turer som Besseggen.",
        "purpose_en": "Promoted physical activity and the outdoors among IFI students, from short forest walks to bigger trips like Besseggen.",
    },
    {
        # No further detail found beyond the name itself -- not guessed at.
        "title": "Lavterskel", "logo": None,
        "purpose_nb": "", "purpose_en": "",
    },
    {
        # No further detail found anywhere -- not guessed at.
        "title": "UPF", "logo": None,
        "purpose_nb": "", "purpose_en": "",
    },
]


class Command(BaseCommand):
    help = (
        "Creates the real IFI/UiO student union pages (if missing), "
        "their en translations, and rebuilds union_groups on both the nb "
        "and en Studentforeninger pages into a row (Sentrale foreninger / "
        "Sittende foreninger i Utvalget) plus one standalone group "
        "(Andre foreninger). Safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created/changed without writing anything.",
        )
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help=(
                "After a fully successful run, delete every logo file in "
                "LOGO_DIR (static/images/studentunions/logos/) -- once "
                "uploaded, the real source of truth is the wagtailimages.Image "
                "records in the database, not these files. Never touches "
                "DEFAULT_LOGO_PATH (the site's own favicon) or anything "
                "outside LOGO_DIR (e.g. seed_dev_data.py's own seed image, "
                "which lives one directory up). Ignored with --dry-run. "
                "Does not delete this command file itself -- that's still "
                "on you."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        cleanup = options["cleanup"]
        self.created_count = 0
        self.skipped_count = 0
        self.logo_errors = False

        try:
            nb_locale = Locale.objects.get(language_code="nb")
            en_locale = Locale.objects.get(language_code="en")
        except Locale.DoesNotExist as exc:
            raise CommandError(
                "Both 'nb' and 'en' Locales must exist -- run migrations/seed data first."
            ) from exc

        nb_category, en_category = self._get_category_pages(nb_locale, en_locale)

        nb_by_title = {}
        en_by_title = {}
        for spec in UNION_SPECS:
            title = spec["title"]
            nb_union = self._get_or_create_union(
                nb_category, nb_locale, title, spec["union_type"], dry_run,
                status=spec.get("status", "active"),
                show_in_menu=spec.get("show_in_menu", False),
            )
            nb_by_title[title] = nb_union

            if dry_run:
                en_by_title[title] = None
                if nb_union is None or not nb_union.has_translation(en_locale):
                    self.stdout.write(f"  would translate UnionPage (en): {title}")
                    self.created_count += 1
                else:
                    self.skipped_count += 1
            else:
                en_by_title[title] = self._translate_union(nb_union, en_locale)

        if not dry_run:
            for spec in UNION_SPECS:
                title = spec["title"]
                logo = self._get_or_create_logo(spec["logo"], title)
                self._enrich_union(
                    nb_by_title[title], spec["purpose_nb"], spec.get("activities_nb", ""),
                    spec.get("vedtekter_nb", ""), spec.get("vedtekter_url", ""),
                    spec.get("website_url", ""), spec.get("signup_url", ""),
                    spec.get("email", ""), spec.get("social", []), logo,
                )
                self._enrich_union(
                    en_by_title[title], spec["purpose_en"], spec.get("activities_en", ""),
                    spec.get("vedtekter_en", ""), spec.get("vedtekter_url", ""),
                    spec.get("website_url", ""), spec.get("signup_url", ""),
                    spec.get("email", ""), spec.get("social", []), logo,
                )

        # Retired unions -- created (if missing) as status="retired", never
        # added to union_groups, only ever shown via the "Old, but not
        # forgotten" section (StudentUnionCategoryPage.get_context()).
        for spec in RETIRED_UNION_SPECS:
            title = spec["title"]
            nb_retired = self._get_or_create_union(
                nb_category, nb_locale, title, spec.get("union_type", "general"),
                dry_run, status="retired",
            )
            if dry_run:
                if nb_retired is None or not nb_retired.has_translation(en_locale):
                    self.stdout.write(f"  would translate UnionPage (en): {title}")
                    self.created_count += 1
                else:
                    self.skipped_count += 1
                continue

            en_retired = self._translate_union(nb_retired, en_locale)
            logo = self._get_or_create_logo(spec.get("logo"), title)
            self._enrich_union(
                nb_retired, spec["purpose_nb"], "", "", "", "", "", "", [], logo,
            )
            self._enrich_union(
                en_retired, spec["purpose_en"], "", "", "", "", "", "", [], logo,
            )

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"Dry run: {self.created_count} page(s)/translation(s) would "
                f"be created, {self.skipped_count} already exist. "
                f"union_groups would be rebuilt on both the nb and en "
                f"Studentforeninger pages."
            ))
            return

        nb_value = self._build_union_groups_value(nb_by_title, lang=0)
        en_value = self._build_union_groups_value(en_by_title, lang=1)

        self._apply_union_groups(nb_category, nb_value, "nb")
        self._apply_union_groups(en_category, en_value, "en")

        self.stdout.write(self.style.SUCCESS(
            f"Done: {self.created_count} page(s)/translation(s) created, "
            f"{self.skipped_count} already existed. Content (purpose/website/"
            f"logo) filled in on any union missing it."
        ))

        if cleanup:
            self._cleanup_logo_dir()

    # -- cleanup ----------------------------------------------------------

    def _cleanup_logo_dir(self):
        """Deletes every file in LOGO_DIR -- only called with --cleanup,
        and only after every union above was successfully created/enriched
        with no logo-file-not-found warnings, since once a file's been
        uploaded the wagtailimages.Image record in the database is the
        real source of truth, not the file on disk. Refuses if any logo
        lookup failed this run (self.logo_errors), so a broken run can't
        delete files a retry might still need."""
        if self.logo_errors:
            self.stdout.write(self.style.WARNING(
                "Skipping --cleanup: at least one logo file was reported "
                "missing above, so LOGO_DIR was left alone -- fix that first."
            ))
            return

        if not LOGO_DIR.exists():
            return

        deleted = 0
        for path in LOGO_DIR.iterdir():
            if path.is_file():
                path.unlink()
                deleted += 1
        try:
            LOGO_DIR.rmdir()
            removed_dir = True
        except OSError:
            removed_dir = False

        self.stdout.write(self.style.SUCCESS(
            f"--cleanup: deleted {deleted} logo file(s) from {LOGO_DIR}"
            + (" and removed the now-empty directory." if removed_dir else ".")
        ))

    # -- content enrichment ---------------------------------------------

    def _get_or_create_logo(self, filename, title):
        """Uploads filename (from LOGO_DIR) as a wagtailimages.Image, or
        returns the existing one on rerun (looked up by title, same
        get-or-create-by-identity convention as the pages themselves).
        filename is None for unions with no official logo found -- falls
        back to a single shared Image of the site's own favicon rather
        than leaving the union without any logo at all."""
        if filename:
            image_title = f"{title} logo"
            path = LOGO_DIR / filename
        else:
            image_title = DEFAULT_LOGO_TITLE
            path = DEFAULT_LOGO_PATH

        existing = Image.objects.filter(title=image_title).first()
        if existing:
            return existing

        if not path.exists():
            self.stdout.write(self.style.WARNING(f"  logo file not found: {path}"))
            self.logo_errors = True
            return None

        with open(path, "rb") as f:
            image = Image(title=image_title, file=ImageFile(f, name=path.name))
            image.save()
        self.stdout.write(f"  uploaded logo image: {image_title}")
        return image

    def _enrich_union(self, union, purpose, activities, vedtekter, vedtekter_url, website_url, signup_url, email, social, logo):
        """Fills purpose/activities/vedtekter/vedtekter_url/website_url/
        signup_url/email/social_links/logo on `union` only where currently
        blank -- never overwrites a value an editor may have since
        hand-edited in Wagtail admin, unlike union_groups above (which this
        script owns outright)."""
        if union is None:
            return
        changed = False
        if purpose and not union.purpose:
            union.purpose = purpose
            changed = True
        if activities and not union.activities:
            union.activities = activities
            changed = True
        if vedtekter and not union.vedtekter:
            union.vedtekter = vedtekter
            changed = True
        if vedtekter_url and not union.vedtekter_url:
            union.vedtekter_url = vedtekter_url
            changed = True
        if website_url and not union.website_url:
            union.website_url = website_url
            changed = True
        if signup_url and not union.signup_url:
            union.signup_url = signup_url
            changed = True
        if email and not union.email:
            union.email = email
            changed = True
        if social:
            existing_pairs = {(b.value["platform"], b.value["url"]) for b in union.social_links}
            new_pairs = [pair for pair in social if pair not in existing_pairs]
            if new_pairs:
                union.social_links = [
                    (b.block_type, {"platform": b.value["platform"], "url": b.value["url"]})
                    for b in union.social_links
                ] + [
                    ("social_link", {"platform": platform, "url": url})
                    for platform, url in new_pairs
                ]
                changed = True
        if logo is not None and union.logo_id is None:
            union.logo = logo
            changed = True
        if changed:
            union.save_revision().publish()
            self.stdout.write(f"  filled in content for: {union.title} ({union.locale.language_code})")

    # -- lookup -------------------------------------------------------

    def _get_category_pages(self, nb_locale, en_locale):
        matches = list(
            StudentUnionCategoryPage.objects.filter(
                slug=CATEGORY_SLUG, locale=nb_locale
            )
        )
        if not matches:
            raise CommandError(
                f"No StudentUnionCategoryPage found with slug={CATEGORY_SLUG!r} "
                "in the nb locale -- this is the same page "
                "core_views.main_view locates via "
                "_get_localized_category('studentforeninger', 'nb', ...). "
                "Verify the slug, or run `python manage.py seed_dev_data` "
                "first on a fresh local DB."
            )
        if len(matches) > 1:
            raise CommandError(
                f"Found {len(matches)} StudentUnionCategoryPage pages with "
                f"slug={CATEGORY_SLUG!r} in the nb locale "
                f"(ids: {[p.id for p in matches]}) -- expected exactly one. "
                "Resolve the ambiguity manually before re-running."
            )
        nb_category = matches[0]

        en_category = nb_category.get_translation_or_none(en_locale)
        if en_category is None:
            raise CommandError(
                f"The nb Studentforeninger page (id={nb_category.id}) has no "
                "English translation yet -- create one in Wagtail admin "
                "('Translate this page') before running this command, so "
                "the real unions can be mirrored into it."
            )
        return nb_category, en_category

    # -- union creation -------------------------------------------------

    def _get_or_create_union(self, category, nb_locale, title, union_type, dry_run, status="active", show_in_menu=False):
        existing = UnionPage.objects.child_of(category).filter(
            title=title, locale_id=nb_locale.id
        ).first()
        if existing:
            self.skipped_count += 1
            changed = False
            if existing.status != status:
                existing.status = status
                changed = True
                self.stdout.write(f"  updated status for: {title} -> {status}")
            if existing.show_in_menu != show_in_menu:
                existing.show_in_menu = show_in_menu
                changed = True
                self.stdout.write(f"  updated show_in_menu for: {title} -> {show_in_menu}")
            if changed and not dry_run:
                existing.save_revision().publish()
            return existing

        if dry_run:
            self.stdout.write(f"  would create UnionPage: {title} ({union_type})")
            self.created_count += 1
            return None

        slug = find_available_slug(category, slugify(title))
        page = UnionPage(
            title=title, slug=slug, locale=nb_locale, union_type=union_type,
            status=status, show_in_menu=show_in_menu,
        )
        category.add_child(instance=page)
        page.save_revision().publish()
        self.created_count += 1
        self.stdout.write(f"  created UnionPage: {title} ({union_type})")
        return page

    def _translate_union(self, nb_union, en_locale):
        """Create nb_union's en translation via wagtail_localize's PO
        pipeline -- same mechanism seed_dev_data.py uses, so the translation
        is properly tracked (not a bare copy_for_translation()). Titles here
        are proper nouns with no msgstr entry, so every segment just falls
        back to the nb source text unchanged, same as seed_dev_data's own
        untranslated-string fallback behavior."""
        if nb_union.has_translation(en_locale):
            self.skipped_count += 1
            return nb_union.get_translation(en_locale)

        source, _ = TranslationSource.get_or_create_from_instance(nb_union)
        translation, _ = Translation.objects.get_or_create(
            source=source, target_locale=en_locale
        )
        po = translation.export_po()
        translation.import_po(po, translation_type="machine", tool_name="setup_union_groups")
        translation.save_target(publish=True)

        en_union = translation.get_target_instance()
        # wagtail_localize doesn't translate slugs -- the title is unchanged
        # here anyway (proper noun), so this is a no-op in practice, kept
        # only for consistency with seed_dev_data's own defensive re-slugify.
        new_slug = slugify(en_union.title)
        if new_slug and new_slug != en_union.slug:
            en_union.slug = find_available_slug(en_union.get_parent(), new_slug)
            en_union.save()

        self.created_count += 1
        self.stdout.write(f"  translated UnionPage (en): {nb_union.title}")
        return en_union

    # -- union_groups value construction ---------------------------------

    def _union_group_value(self, title, titles, by_title):
        return {
            "title": title,
            "general_info": "",
            "unions": [{"union": by_title[t]} for t in titles],
        }

    def _build_union_groups_value(self, by_title, lang):
        """lang: 0 for nb title, 1 for en title, matching the (nb, en,
        members) tuples in ROW_GROUP_SPECS/STANDALONE_GROUP_SPECS."""
        return [
            ("row", {
                "title": "",
                "groups": [
                    self._union_group_value(spec[lang], spec[2], by_title)
                    for spec in ROW_GROUP_SPECS
                ],
            }),
        ] + [
            ("group", self._union_group_value(spec[lang], spec[2], by_title))
            for spec in STANDALONE_GROUP_SPECS
        ]

    # -- idempotency check + write ------------------------------------------

    def _apply_union_groups(self, category, new_value, label):
        if self._signature(category.union_groups) == self._signature_of_value(new_value):
            self.stdout.write(f"  union_groups ({label}) already matches -- no change.")
            return
        category.union_groups = new_value
        category.save_revision().publish()
        self.stdout.write(f"  union_groups ({label}) updated.")

    def _signature(self, stream_value):
        """Reduce a live union_groups StreamValue to a comparable, order-
        sensitive nested tuple -- mirrors how the templates themselves walk
        block/group/unions (studentunion_category_page.html + union_group.html)."""
        sig = []
        for block in stream_value:
            if block.block_type == "group":
                sig.append(("group", self._group_signature(block.value)))
            elif block.block_type == "row":
                sig.append((
                    "row",
                    block.value.get("title") or "",
                    tuple(self._group_signature(g) for g in block.value["groups"]),
                ))
        return tuple(sig)

    def _group_signature(self, group_value):
        # item["union"] resolves to None if the referenced page was since
        # deleted (a stale PageChooserBlock reference) -- tolerate that
        # rather than crashing, so a rebuild can clean it up.
        return (
            group_value["title"],
            str(group_value.get("general_info") or ""),
            tuple(
                item["union"].id if item["union"] else None
                for item in group_value["unions"]
            ),
        )

    def _signature_of_value(self, raw_value):
        """Same shape as _signature(), computed directly from the python
        list-of-tuples about to be assigned (avoids round-tripping through a
        real StreamValue just to compare)."""
        sig = []
        for block_type, value in raw_value:
            if block_type == "group":
                sig.append(("group", self._raw_group_signature(value)))
            elif block_type == "row":
                sig.append((
                    "row",
                    value["title"] or "",
                    tuple(self._raw_group_signature(g) for g in value["groups"]),
                ))
        return tuple(sig)

    def _raw_group_signature(self, value):
        return (
            value["title"],
            value.get("general_info") or "",
            tuple(item["union"].id for item in value["unions"]),
        )
