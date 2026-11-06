# Réglages des prochaines vidéos — 5 novembre 2026

Profil actif : `balanced_audio_v2`. La programmation et la publication restent
désactivées ; ce réglage ne constitue pas une autorisation de dépense récurrente.

## Son et montage

Les clips source restent générés sans audio pour conserver le tarif économique.
Le montage final ajoute systématiquement une musique ambiante originale, composée
localement à partir d'oscillateurs, sans enregistrement ni morceau externe.
L'asset et sa provenance sont inclus dans le paquet déployé. Le montage s'arrête si
le morceau manque : il ne remplace pas discrètement le résultat par une vidéo muette.

Le niveau cible est -24 LUFS avec entrée/sortie progressives. Le fichier final utilise
une piste AAC stéréo ; sa durée et son niveau sonore sont contrôlés. Une piste vide
ou silencieuse échoue au contrôle. La copie d'analyse conserve le son.

Un fondu court de 0,2 seconde adoucit le raccord entre les deux clips. Deux sources de
8 secondes donnent un montage de 15,8 secondes, dans la cible de 15 à 20 secondes.
Ce fondu ne garantit pas de corriger tous les défauts de mouvement des images sources.
Pour fonctionner sur le VPS de 1 Go, le début, le court raccord et la fin sont encodés
séparément puis assemblés sans réencodage vidéo supplémentaire. Le montage réel avec
les sources existantes a réussi dans la limite actuelle de 384 Mo du processus.

## Contrôle pragmatique

Le seuil reste 80/100. Les détails mineurs ou visibles uniquement en arrêt sur image
ou avec zoom sont tolérés. Un défaut important doit avoir des repères temporels et
une description concrète de ce qui gêne à vitesse normale sur téléphone.

- Défaut mineur et score suffisant : accepté, puis validation humaine habituelle.
- Problème visible corrigeable par montage : `local_edit` / `awaiting_local_edit`.
- Doute, score faible, son non observable ou affirmation sans preuve : examen manuel.
- Échec objectif du fichier (format, décodage, son absent/silencieux) : blocage technique.

Aucune de ces décisions ne lance automatiquement une nouvelle génération payante.
Le format historique du premier contrôle est conservé pour audit. Le premier essai
rejeté n'est pas reclassé comme accepté par simple changement de règles.

## Vérification et limites

Le montage réel, la piste audible et sa conservation dans la requête d'analyse ont été
testés. Les 14 scénarios HTTP Postman couvrent l'acceptation d'un défaut mineur,
l'orientation vers le montage d'un défaut majeur, les cas douteux, le son non observable,
et les incidents fournisseur/budget précédents. 71 tests du projet passent.
La simulation vérifie le comportement du code ; elle ne prouve pas comment le modèle
réel jugera le prochain contenu. Aucun nouvel appel IA payant n'a été exécuté pour
installer ou vérifier ces réglages.
Les 27 vérifications du studio passent après installation. Le profil est visible dans
l'API protégée et le tableau de bord. Le coût enregistré reste 0,800526 $ et il n'existe
aucune publication. La première vidéo et son contrôle historique sont conservés.

La production autonome et la publication ne sont pas activées. Prochaine étape :
écouter l'aperçu issu des clips déjà payés, valider l'ambiance et le raccord, puis
réaliser un nouvel essai manuel avant d'envisager la programmation.
