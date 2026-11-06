"""Factual Google-branding pages; private drafts until the owner approves publication."""

from html import escape

from fastapi import Request
from fastapi.responses import HTMLResponse

CONTENT = {
    "about": (
        "TechnoInno Studio",
        """
<p class="lead">Un studio privé pour créer et publier les vidéos originales de TechnoInno.</p>
<p>TechnoInno Studio prépare des vidéos verticales apaisantes : scènes macro, mouvements
simples, textures et bruitages liés à l’action. Les images sont générées par intelligence
artificielle. Les titres et descriptions peuvent être proposés en six langues.</p>
<h2>Une application réservée à son administrateur</h2>
<p>Le studio utilise les services API de YouTube pour connecter la chaîne autorisée,
téléverser ses propres vidéos et gérer leurs titres, descriptions et visibilité.
Il ne propose pas d’inscription publique et n’est pas un service de Google ou de YouTube.</p>
<p>Les générations payantes et les publications programmées exigent une configuration
et une autorisation distinctes. Connecter Google ne lance pas de production.</p>
<p>Contact de l’administrateur :
<a href="mailto:admin.technoinno@gmail.com">admin.technoinno@gmail.com</a>.</p>
<p><a class="button" href="/login">Accéder au studio</a></p>
""",
    ),
    "privacy": (
        "Confidentialité",
        """
<p class="lead">Cette politique décrit le fonctionnement de TechnoInno Studio,
application privée de gestion de la chaîne TechnoInno.</p>
<h2>Données utilisées et finalités</h2>
<p>La connexion Google donne au studio l’identifiant de la chaîne autorisée, ses
permissions et les jetons nécessaires à l’accès YouTube. Le studio conserve les
identifiants et états des vidéos qu’il téléverse, ainsi que leurs métadonnées.
Ces informations servent uniquement à connecter la bonne chaîne, publier les contenus
autorisés, vérifier leur état et éviter les téléversements en double.</p>
<p>Le studio conserve également ses propres scénarios, contenus générés, contrôles de
qualité, coûts et journaux de fonctionnement. Il ne demande pas le mot de passe Google.</p>
<h2>Prestataires et partage</h2>
<p>Google et YouTube assurent l’authentification et les opérations sur la chaîne.
OpenRouter et les fournisseurs de modèles traitent les consignes et contenus originaux
nécessaires à la génération et au contrôle. Les jetons Google ne leur sont pas envoyés.
Les données sont hébergées sur le VPS Hostinger de l’administrateur ; des sauvegardes
chiffrées sont conservées sur un support distinct sous son contrôle.</p>
<p>Si les alertes par courriel sont activées, le prestataire de messagerie reçoit
l’adresse du destinataire et une alerte générale, sans jeton Google ni erreur brute.
Les données Google ne sont ni vendues, ni utilisées pour le ciblage publicitaire,
ni utilisées par ce studio pour entraîner des modèles d’IA.</p>
<h2>Protection, cookies et conservation</h2>
<p>Les accès au studio utilisent HTTPS. Les jetons Google sont chiffrés dans la base.
Les cookies servent à la connexion et à la protection des formulaires ; la session
administrateur expire après huit heures. Le studio n’installe pas de cookie publicitaire.</p>
<p>L’administrateur conserve les données nécessaires au fonctionnement du studio.
Il doit actualiser ou supprimer les données issues des API YouTube au moins tous les
30 jours selon les règles de YouTube. Cette maintenance reste sous sa responsabilité.
Les contenus créés par le studio et les relevés de coûts sont gérés séparément.</p>
<h2>Retrait de l’accès et suppression</h2>
<p>L’accès peut être révoqué depuis les
<a href="https://security.google.com/settings/security/permissions">
paramètres de sécurité Google</a>.
Une demande de consultation, de correction ou de suppression des données du studio
peut être adressée à <a href="mailto:admin.technoinno@gmail.com">admin.technoinno@gmail.com</a>.
L’administrateur traite manuellement les demandes de suppression des données YouTube
dans un délai maximal de sept jours et prend en compte les copies de secours.
Une suppression dans le studio ne supprime pas une vidéo déjà publiée sur YouTube.</p>
<p>L’utilisation et le transfert d’informations reçues des API Google doivent respecter
la <a href="https://developers.google.com/terms/api-services-user-data-policy">
Google API Services User Data Policy</a>,
y compris ses exigences Limited Use. Voir également la
<a href="https://policies.google.com/privacy">politique de confidentialité de Google</a>.</p>
""",
    ),
    "terms": (
        "Conditions d’utilisation",
        """
<p class="lead">TechnoInno Studio est un outil privé réservé à l’administrateur
autorisé de la chaîne TechnoInno.</p>
<h2>Utilisation et contrôle</h2>
<p>L’utilisateur doit disposer des droits nécessaires sur la chaîne et sur les contenus
qu’il demande de créer ou de publier. Il garde le contrôle des autorisations Google,
des plafonds de dépenses, des horaires et des paramètres de publication.</p>
<p>Le studio utilise les services API de YouTube. En utilisant ses fonctions YouTube,
l’utilisateur accepte d’être lié par les
<a href="https://www.youtube.com/t/terms">conditions d’utilisation de YouTube</a>.
L’utilisation du studio implique également l’acceptation de sa
<a href="/privacy">politique de confidentialité</a>.</p>
<h2>Création, qualité et coûts</h2>
<p>Les contenus sont générés avec une IA et peuvent nécessiter une correction.
Les contrôles automatiques n’apportent aucune garantie d’absence de défaut,
de disponibilité, de nombre de vues ou de revenus.</p>
<p>Les services de génération peuvent être payants selon leurs tarifs et conditions.
La programmation et les plafonds sont configurés séparément. Une opération interrompue
peut avoir été facturée par un fournisseur ; une dépense incertaine reste comptabilisée
par prudence jusqu’à son rapprochement. Aucune régénération payante automatique n’est prévue.</p>
<h2>Confidentialité et arrêt</h2>
<p>L’administrateur doit protéger ses accès, limiter les permissions aux besoins du
studio et arrêter la production si nécessaire. Il peut révoquer la connexion Google
et demander la suppression des données selon la politique de confidentialité.</p>
<p>Contact : <a href="mailto:admin.technoinno@gmail.com">admin.technoinno@gmail.com</a>.</p>
""",
    ),
}


def render(name, *, draft=True):
    title, body = CONTENT[name]
    banner = (
        "<aside>Brouillon privé à relire par l’administrateur avant publication.</aside>"
        if draft
        else ""
    )
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · TechnoInno Studio</title><style>
body{{margin:0;background:#f4f7fa;color:#173342;font:17px/1.65 system-ui,sans-serif}}
main{{max-width:820px;margin:40px auto;padding:32px;background:white;border-radius:20px}}
nav{{display:flex;gap:20px;flex-wrap:wrap;font-size:15px}}a{{color:#086477}}
h1{{font-size:38px;line-height:1.2}}h2{{margin-top:30px;font-size:23px}}
.lead{{font-size:20px}}aside{{padding:14px;background:#fff0c4;border-radius:10px}}
footer{{margin-top:40px;font-size:14px;color:#4b606c}}.button{{display:inline-block;
padding:10px 20px;background:#086477;color:white;border-radius:8px;text-decoration:none}}
@media(max-width:650px){{main{{margin:12px;padding:22px}}h1{{font-size:30px}}}}
</style></head><body><main><nav><a href="/about">Présentation</a>
<a href="/privacy">Confidentialité</a><a href="/terms">Conditions</a></nav>
<h1>{escape(title)}</h1>{banner}{body}
<footer>TechnoInno Studio · Version du 5 novembre 2026</footer>
</main></body></html>"""


def register(app, settings, access):
    for name in CONTENT:

        def endpoint_for(page):
            async def endpoint(request: Request):
                if not settings.public_information_approved:
                    await access(request)
                return HTMLResponse(render(page, draft=not settings.public_information_approved))

            return endpoint

        app.add_api_route(
            "/" + name,
            endpoint_for(name),
            methods=["GET"],
            include_in_schema=False,
            response_class=HTMLResponse,
        )
