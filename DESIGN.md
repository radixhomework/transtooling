---
name: TransTooLing
description: Atelier local de transcription et de traduction — confidentiel par architecture.
colors:
  accent: "#2f5d57"
  accent-hover: "#244844"
  accent-soft: "#e2ebe9"
  bg: "#f6f5f2"
  surface: "#ffffff"
  surface-sunken: "#edece7"
  ink: "#1b211f"
  ink-soft: "#4b524f"
  ink-faint: "#8a908d"
  border: "#dedad2"
  border-strong: "#c7c2b8"
  status-pending: "#b8863a"
  status-pending-soft: "#f5ead4"
  status-done: "#2f5d57"
  status-done-soft: "#e2ebe9"
  status-error: "#a24c3d"
  status-error-soft: "#f6e2de"
typography:
  title:
    fontFamily: "Space Grotesk, Segoe UI, sans-serif"
    fontSize: "1.6rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Space Grotesk, Segoe UI, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "IBM Plex Mono, SFMono-Regular, Consolas, monospace"
    fontSize: "0.72rem"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "0.02em"
rounded:
  sm: "6px"
  md: "10px"
  lg: "16px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "10px 16px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "10px 16px"
  button-danger:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.status-error}"
    rounded: "{rounded.sm}"
    padding: "10px 16px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "20px"
  badge:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    rounded: "999px"
    padding: "4px 10px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
---

# Design System: TransTooLing

## Overview

**Creative North Star: "L'Atelier local"**

TransTooLing se présente comme un atelier sobre et bien rangé : des surfaces
papier chaudes, des outils précis toujours à la même place, et une couleur —
le vert mousse — réservée aux actions et aux états positifs. Rien ne hurle,
tout est prévisible ; l'utilisateur vient faire un travail, pas vivre une
expérience. La densité est faible (une action principale par vue), la
hiérarchie repose sur la typographie et l'aération plutôt que sur la couleur
ou les ombres.

La voix des données est distincte de la voix de l'interface : IBM Plex Mono
porte identifiants, noms de modèles, dates, tailles et états, comme les
étiquettes d'un atelier ; Space Grotesk porte les phrases. Le composant
signature est la forme d'onde — cinq barres verticales qui pulsent dès qu'un
traitement est en cours — déclinée de la marque au dashboard.

**Key Characteristics:**
- Surfaces papier chaudes et plates ; profondeur par tons, presque jamais par ombres
- Une seule couleur d'expression : le vert mousse, rare et réservé (actions, actif, terminé)
- Deux voix typographiques : Space Grotesk pour l'humain, IBM Plex Mono pour la donnée
- La forme d'onde comme signature animée du travail en cours
- Composants sobres et rassurants : transitions douces (0,15 s), rien ne surprend

## Colors

Palette resserrée d'atelier : papier chaud, encres grises, un vert mousse
artisanal et trois teintes d'état factuelles.

### Primary
- **Vert mousse** (#2f5d57) : la seule couleur d'expression. Boutons
  primaires, liens, état actif de navigation, focus, forme d'onde, statut
  « terminé ». Sa rareté est sa force.
- **Vert mousse profond** (#244844) : unique variante, au survol du bouton primaire.
- **Vert mousse pâle** (#e2ebe9) : fond des badges et de l'état actif de
  navigation — la voix douce du vert.

### Neutral
- **Papier chaud** (#f6f5f2) : fond de page, ton dominant de l'atelier.
- **Surface blanche** (#ffffff) : cartes, en-tête, champs.
- **Surface enfoncée** (#edece7) : pistes de progression, onglets inactifs,
  textes préformatés — la profondeur par ton, pas par ombre.
- **Encre** (#1b211f) : texte principal.
- **Encre douce** (#4b524f) : texte secondaire, navigation au repos.
- **Encre pâle** (#8a908d) : métadonnées, dates, légendes.
- **Bord chaud** (#dedad2) : séparateurs, bordures de cartes.
- **Bord franc** (#c7c2b8) : bordures de champs et de boutons secondaires.

### Tertiary
- **Ambre d'attente** (#b8863a sur #f5ead4) : en cours, en attente.
- **Brique d'erreur** (#a24c3d sur #f6e2de) : erreurs, suppression.

### Named Rules
**La règle de la couleur rare.** Le vert mousse couvre au plus ~10 % d'un
écran. S'il devient décoratif, il cesse d'être un signal.

## Typography

**Display/Title Font:** Space Grotesk (Segoe UI, sans-serif)
**Body Font:** Space Grotesk (Segoe UI, sans-serif)
**Label/Mono Font:** IBM Plex Mono (SFMono-Regular, Consolas, monospace)

**Character:** Un grotesque contemporain légèrement technique pour les
phrases, doublé d'un mono sobre pour la donnée — l'étiquette et l'outil,
pas la vitrine.

### Hierarchy
- **Title** (600, 1,6 rem, 1,2, letter-spacing -0,01 em) : titre unique de
  chaque page (h1).
- **Body** (400, 0,95 rem, 1,5) : paragraphes, descriptions, libellés de
  formulaires (0,8–0,88 rem pour les secondaires).
- **Label** (500, 0,72 rem, letter-spacing 0,02 em, MAJUSCULES) : badges,
  en-têtes de tableaux, formats de fichiers, identifiants, tailles, dates —
  tout ce qui est donnée.

### Named Rules
**La règle des deux voix.** Toute valeur mesurable ou technique (nom de
modèle, identifiant, timestamp, taille) passe en IBM Plex Mono ; toute
phrase passe en Space Grotesk. Jamais l'inverse.

## Layout

Coque applicative unique : en-tête sticky (64 px, surface blanche, bord
inférieur) contenant marque, navigation et compte ; contenu centré
(max-width 1040 px, padding 40 px 24 px 80 px). Chaque page est une colon
flex avec un rythme de 24 px entre sections. Les grilles de cartes
(modèles, utilisateurs) sont en auto-fill minmax(220 px, 1 fr). Sous
720 px, l'en-tête s'enveloppe et la navigation passe en défilement
horizontal pleine largeur. Les tableaux restent des tableaux — pas de
transformation en cartes sur mobile à ce jour.

## Elevation & Depth

**Plat par défaut.** La profondeur vient des tons (surface → surface
enfoncée) et de bordures fines ; une seule ombre existe dans tout le
système, ambiante et quasi imperceptible, sous les cartes
(`0 1px 2px rgba(27,33,31,0.04), 0 4px 16px rgba(27,33,31,0.05)`). L'en-tête
sticky n'ombre pas : il se contente d'un bord.

### Named Rules
**La règle du plat au repos.** Aucune ombre n'apparaît en réponse à un
état (survol, focus). Les états se marquent par le ton ou la couleur,
jamais par une élévation.

## Shapes

Rayons doux et mesurés : 6 px (boutons, champs, badges d'onglet), 10 px
(menus, onglets), 16 px (cartes, modales) ; pilule complète (999 px)
uniquement pour les badges de statut. Bordures 1 px en gris chaud partout
où deux surfaces se rencontrent. La géométrie signature est verticale et
fine : les barres de la forme d'onde et de la marque (2–4 px de large,
coins 2 px) — un motif d'égaliseur discret qui relie la marque au travail.

## Components

### Buttons
- **Shape:** coins doux (6 px)
- **Primary:** vert mousse plein, texte blanc, padding 10 px 16 px ;
  variante compacte 6 px 12 px (0,8 rem)
- **Hover / Focus:** assombrissement vers le vert profond (0,15 s) ;
  focus visible : contour 2 px vert mousse, décalé de 2 px
- **Secondary:** surface blanche, bord franc, texte encre
- **Danger:** surface blanche, bord et texte brique ; fond brique pâle au survol
- **Disabled:** opacité 0,5, curseur interdit

### Chips / Badges
- **Style:** pilule (999 px), IBM Plex Mono 0,72 rem majuscules ; fond doux
  + texte coloré : vert mousse pâle/vert (terminé, actif), ambre pâle/ambre
  (attente, en cours, annulation), brique pâle/brique (erreur), enfoncé/encre
  douce (annulé)
- **Comportement:** le badge « en cours » embarque la forme d'onde taille sm ;
  il peut afficher un pourcentage (« En cours · 42 % »)

### Cards / Containers
- **Corner Style:** 16 px
- **Background:** surface blanche sur fond papier
- **Shadow Strategy:** l'unique ombre ambiante (voir Elevation)
- **Border:** 1 px bord chaud ; bord vert mousse sur la carte « par défaut »
- **Internal Padding:** 16–24 px, flex column, écart 12 px

### Inputs / Fields
- **Style:** surface blanche, bord franc 1 px, coins 6 px, padding 10 px 12 px
- **Focus:** bord qui passe au vert mousse (pas de halo)
- **Labels:** 0,8 rem, encre douce, au-dessus du champ

### Navigation
- Liens texte 0,88 rem (500), encre douce au repos, fond enfoncé + encre au
  survol, fond vert mousse pâle + texte vert à l'état actif ; coins 6 px,
  padding 8 px 12 px

### Waveform (composant signature)
Cinq barres verticales vert mousse (3 px, coins 2 px) qui pulsent en
oscillation douce (0,9 s, ease-in-out, hauteur 25 % ↔ 100 %, décalage par
barre). Trois tailles : sm (14 px, badges), md (20 px), lg (32 px, envoi).
C'est l'indicateur universel de traitement — il remplace tout spinner.
Désactivée sous `prefers-reduced-motion`.

### Progress bar
Piste enfoncée (6 px, pilule) et remplissage vert mousse mis à l'échelle
horizontalement (scaleX, 0,4 s — sans reflow) ; pourcentage en IBM Plex Mono
0,72 rem. Utilisée pour la progression de transcription et l'envoi d'archives.

## Do's and Don'ts

### Do:
- **Do** garder le vert mousse minoritaire : actions, actif, terminé —
  rien d'autre.
- **Do** passer toute donnée technique en IBM Plex Mono (règle des deux voix).
- **Do** marquer les états par le ton ou une couleur de statut, avec des
  transitions de 0,15 s.
- **Do** utiliser la forme d'onde comme unique indicateur d'attente animée.
- **Do** conserver l'unique ombre ambiante pour les cartes et une seule
  action principale par vue.

### Don't:
- **Don't** introduire une deuxième couleur d'expression, un dégradé ou une
  ombre portée d'état.
- **Don't** mettre du texte long en IBM Plex Mono — le mono est réservé aux
  valeurs courtes.
- **Don't** superposer les modales ; une seule à la fois (déjà le cas).
- **Don't** animer autre chose que la forme d'onde, la largeur des barres de
  progression et les transitions de couleur de 0,15 s.
