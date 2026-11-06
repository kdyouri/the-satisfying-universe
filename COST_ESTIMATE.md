# Coûts et choix économiques — 5 novembre 2026

La préférence du propriétaire est désormais : coût bas et qualité suffisante.
Ce document remplace l'estimation initiale centrée sur des modèles plus chers.
Les plafonds effectifs restent **0 $/jour et 0 $/mois**, sans dépense autorisée.

## Résultat de l'essai autorisé — terminé en privé

Vidéo G9wNpynDbPY, 91/100, musique et six langues, traitement HD confirmé. Coût réel
confirmé : **0,800908 USD** ; réserves conservées pour trois contrôles sans coût
individuel réconcilié : **0,14 USD**. Exposition totale : 0,940908 USD, sous le plafond
explicitement autorisé de 1 USD, y compris deux appels supplémentaires confirmés par
le propriétaire. Les clips n'ont pas été régénérés. Les plafonds récurrents restent à zéro.

La correction utilise Google AI Studio standard dans les mêmes plafonds de prix ;
la sélection économique des autres rôles reste inchangée. Les tarifs Flex nouvellement
moins chers n'ont pas été validés pour ce contrôle et sont exclus de cette route.
Les propositions ci-dessous sont historiques et ne sont pas de nouvelles autorisations.

## Proposition actuelle — un essai privé plafonné à 1 USD

Le parcours réutilisable est installé et testé avec des fournisseurs simulés. Aucun
nouvel appel réel payant n'a été lancé. Le prochain essai proposé est une goutte d'eau
sur une feuille en céramique bleue, deux clips de 8 secondes, montage final de 15,8 s,
musique originale et métadonnées en six langues. Génération prévue : 0,80 USD ;
réservations maximales des étapes : 0,86 USD ; plafond supplémentaire demandé :
**1,00 USD pour cet essai unique privé**, soumis à l'autorisation explicite du propriétaire.
Pas de régénération payante automatique. Les plafonds récurrents restent à zéro.

Catalogue revérifié le 5 novembre sans clé ni dépense : Gemma 4 26B A4B coûte
0,038/0,113 USD par million de tokens entrée/sortie, Gemini 3.1 Flash Lite
0,25/1,50 USD, et Veo 3.1 Lite 1080p sans audio 0,05 USD/s. Le prix Gemma remplace
l'ancienne valeur 0,027/0,08 ci-dessous. Le nouveau parcours revalide les prix avant
soumission, conserve les réservations incertaines et n'applique aucun abonnement.
Coût confirmé du premier échantillon existant : 0,800526 USD ; deux anciennes
réservations incertaines de 0,06 USD au total restent conservées.

Preuves : docs/evidence/production-workflow-model-preflight-2026-11-05.json et
production-private-trial-proposal-2026-11-05.json. Les sections suivantes conservent
l'étude du 4 novembre ; leurs mentions « à implémenter » sont historiques.

## Profil de départ configuré

| Usage | Modèle candidat | Tarif catalogue USD |
|---|---|---|
| Idées, prompts et métadonnées | google/gemma-4-26b-a4b-it | 0,027 $ / million de tokens en entrée ; 0,08 $ en sortie |
| Contrôle visuel vidéo | google/gemini-3.1-flash-lite | 0,25 $ / million de tokens en entrée ; 1,50 $ en sortie |
| Génération principale | google/veo-3.1-lite | 1080p vertical, sans audio : 0,05 $/seconde |

Ce sont des candidats configurés, pas des modèles déjà validés sur nos contenus.
Les adaptateurs de génération et de revue vidéo restent à implémenter. Aucun appel
payant n'a été lancé. Le modèle de contrôle vidéo est distinct du modèle générateur.

## Coût réel du format cible

Le catalogue expose des clips Veo Lite de 4, 6 ou 8 secondes, pas une demande de
16 secondes. Le plan cible est **deux clips complémentaires de 8 secondes**, soit
16 secondes au total. Le raccord doit passer le contrôle qualité ; on ne suppose
ni rallongement artificiel ni continuité parfaite entre deux générations.

| Option | Format et plan | SKU exact | Coût génération / tentative |
|---|---|---|---:|
| Veo 3.1 Lite — principal | 1080p, 9:16, 2 × 8 s, sans audio | duration_seconds_without_audio = 0.05 USD/s | 0,80 $ |
| Veo 3.1 Lite — variante économique | 720p, 9:16, 2 × 8 s, sans audio | duration_seconds_without_audio_720p = 0.03 USD/s | 0,48 $ |
| Grok Imagine Video 1.5 Lite — comparatif | 720p, 9:16, 1 × 15 s | cents_per_video_output_second_720p = 3 cents/s | 0,45 $ |
| Veo 3.1 Fast — ancien candidat | 1080p, 9:16, 2 × 8 s, sans audio | duration_seconds_without_audio = 0.10 USD/s | 1,60 $ |

Les unités sont importantes : un SKU en cents doit être divisé par 100 ; les
modèles Seedance sont facturés en tokens vidéo et demandent un calcul par pixels,
durée et fréquence. Un prix public « à partir de » ne suffit pas pour un devis.
Les tarifs sans suffixe 720p de Veo correspondent au palier 1080p dans ce catalogue.
Revalider le couple résolution/durée/audio et le tarif routé avant chaque appel payant.

Le mode audio Grok Lite n'est pas précisé dans le catalogue ; ne pas inventer un
paramètre pour le désactiver. Le comparatif ci-dessus utilise uniquement son tarif
text-to-video 720p, sans image de référence ni option supplémentaire.

## Deux originaux par jour — génération uniquement

Sur 30 jours, l'objectif représente 60 originaux. Les reprises ne garantissent pas
qu'une tentative devienne une vidéo acceptée.

| Option | 60 tentatives | 75 tentatives : +25 % | 120 tentatives : deux par original |
|---|---:|---:|---:|
| Veo Lite 1080p | 48,00 $ | 60,00 $ | 96,00 $ |
| Veo Lite 720p | 28,80 $ | 36,00 $ | 57,60 $ |
| Grok Lite 720p | 27,00 $ | 33,75 $ | 54,00 $ |

Ces montants excluent les modèles de texte/revue, le VPS, le stockage, les frais
d'achat de crédit et les taxes. Ce ne sont pas des budgets autorisés.
À titre d'arithmétique seulement, 3 000 tokens d'entrée + 1 000 de sortie avec Gemma
coûtent 0,000161 $, et 10 000 tokens d'entrée + 1 000 de sortie avec Gemini Flash
Lite coûtent 0,004 $. La tokenisation des vidéos, l'audio, le raisonnement et les
reprises détermineront la consommation réelle ; aucune consommation n'a été mesurée.

## Équilibre coût / qualité

Conserver le seuil existant de 80/100 et les veto techniques/défauts graves.
Optimiser le coût par vidéo acceptée : un modèle moins cher mais souvent rejeté
peut coûter plus cher. Vérifier les mouvements, les textures, le raccord et la stabilité.
Faire FFmpeg/FFprobe avant une revue IA payante. Utiliser des sorties JSON bornées.
Pas de modèle premium en secours automatique ; en cas d'incertitude, arrêter et
revoir le résultat. Au maximum une reprise de génération, toujours sous le plafond.

Le 1080p natif reste le profil principal. Le 720p est une variante de coût à tester,
pas du 1080p natif après agrandissement. Grok Lite annonce explicitement que sa sortie
1080p est agrandie à partir de 720p ; payer ce palier n'est pas retenu pour ce projet.

Seedance 1.5 Pro est écarté malgré son prix attractif : sa page annonce un retrait le
11 novembre 2026. Mischief 1, encore moins cher, ne propose que de l'image-to-video
horizontal ; il ne répond pas au format vertical cible sans changement de pipeline.
Les tarifs et descriptions ne démontrent pas la qualité sur les vidéos de TechnoInno.

## Petit essai proposé — pas encore autorisé

Remplacer le précédent benchmark coûteux par trois concepts simples (liquide,
mouvement mécanique, paysage miniature), chacun en Veo Lite 1080p (0,80 $), Veo
Lite 720p (0,48 $) et Grok Lite 720p (0,45 $). Neuf versions : **5,19 $** de
vidéo avant contrôle/éventuelle reprise. Les différences de résolution/durée sont
volontaires : on compare des options de coût/qualité, pas un classement à paramètres
identiques. Une enveloppe maximale de 10 $ serait une proposition de premier essai,
pas une autorisation. La préparation des adaptateurs et une limite explicite du
propriétaire restent nécessaires avant son lancement. Aucune publication incluse.

## Sources et preuve

- [Catalogue vidéo OpenRouter](https://openrouter.ai/api/v1/videos/models), 31 modèles relevés.
- [Catalogue général OpenRouter](https://openrouter.ai/api/v1/models), 454 modèles relevés.
- [Documentation vidéo](https://openrouter.ai/docs/guides/overview/multimodal/video-generation).
- [Veo 3.1 Lite](https://openrouter.ai/google/veo-3.1-lite).
- [Grok Imagine Video 1.5 Lite](https://openrouter.ai/x-ai/grok-imagine-video-1.5-lite).
- [Gemma 4 26B A4B](https://openrouter.ai/google/gemma-4-26b-a4b-it).
- [Gemini 3.1 Flash Lite](https://openrouter.ai/google/gemini-3.1-flash-lite).
- [Retrait annoncé de Seedance 1.5 Pro](https://openrouter.ai/bytedance/seedance-1-5-pro).

Données brutes et sélection chiffrée : docs/evidence/*low-cost*2026-11-04.json.
L'ancien chiffrage est conservé dans docs/evidence/cost-estimate-initial-2026-11-04.md.
