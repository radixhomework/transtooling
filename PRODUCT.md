# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Petite équipe : quelques collègues se connectent avec leur compte (identifiant
simple + mot de passe, pas d'email) ; un administrateur gère les utilisateurs,
les modèles et les paramètres. Interface intégralement en français.

## Product Purpose

TransTooLing est une application auto-hébergée qui transcrit des fichiers
audio en français (texte horodaté, export .vtt ou .txt) et traduit du texte
ou des archives de fichiers techniques (JSON, HTML, Markdown) entre le
français et l'anglais. Les deux usages sont à égalité et quotidiens. Le
succès : ces deux tâches accomplies intégralement en local, sans qu'aucune
donnée ne quitte la machine.

## Positioning

Traitement 100 % local (faster-whisper et NLLB/CTranslate2 sur CPU) :
confidentialité des contenus garantie par l'architecture, sans dépendance à
un service tiers ni coût récurrent — ce qu'un service cloud ne peut pas
promettre de manière vérifiable.

## Operating Context

- Déploiement Docker Compose (backend FastAPI, frontend React/Vite servi par
  Nginx, worker de transcription et worker de traduction séquentiels),
  derrière un reverse proxy Apache en production, exposé en local uniquement.
- Files traitées une à une ; suivi de statut et de progression par polling ;
  annulation possible en cours de traitement.
- Modèles téléchargés à la demande depuis le panneau d'administration.

## Capabilities and Constraints

- Transcription : mp3/wav/m4a/ogg/webm ; l'audio source est toujours supprimé
  après traitement, seul le texte résultat est conservé.
- Traduction : texte manuel ou archives ZIP (noms et arborescence conservés,
  syntaxe Markdown/HTML/JSON préservée, chemins et code jamais traduits) ;
  cache des traductions en base.
- Authentification par identifiant simple, rôles user/admin, protection
  brute-force sur le login.
- CPU uniquement (pas de GPU) ; SQLite partagée backend/workers ; limites de
  taille, durée et extensions configurables par l'admin.
- Modèle de traduction actuel (NLLB-200-distilled-600M via CTranslate2) sous
  licence CC-BY-NC 4.0 : usage non commercial.

## Brand Commitments

- Nom : TransTooLing (choisi explicitement par l'utilisateur).
- Interface en français, uniquement.

## Evidence on Hand

- Code complet et instance locale fonctionnelle (`docker compose up`) ;
  README.md et CLAUDE.md documentent l'architecture et les décisions.
- Aucun contenu réel de démonstration, témoignage, capture ou jeu de
  données : ne pas en inventer lors de travaux futurs.

## Product Principles

1. Aucune donnée ne quitte la machine — promesse architecturale, pas un
   argument marketing.
2. La simplicité prime : parcours courts, erreurs explicites en français,
   réglages complexes réservés au panneau admin.
3. Autonomie : fonctionne sur une machine modeste, CPU seul, sans service
   payant.
4. Transcription et traduction sont des usages de premier rang, à égalité.
5. Les fichiers sources ne sont jamais conservés au-delà du traitement.
