---
name: TransTooLing
description: Atelier local de transcription et de traduction — charte éditoriale radixhomework.
colors:
  accent: "#4D5947"
  accent-hover: "#3F4A3B"
  accent-soft: "#e3e7dd"
  copper: "#9A7656"
  copper-soft: "#efe6dc"
  bg: "#fcfcfa"
  surface: "#fdfaf3"
  surface-sunken: "#eae5d8"
  parchment: "#d8d0bd"
  ink: "#1E211C"
  ink-soft: "#76604E"
  ink-faint: "#a18f7c"
  border: "rgba(30, 33, 28, 0.2)"
  border-strong: "rgba(30, 33, 28, 0.4)"
  status-pending: "#9A7656"
  status-pending-soft: "#efe6dc"
  status-done: "#4D5947"
  status-done-soft: "#e3e7dd"
  status-error: "#8A5E61"
  status-error-soft: "#efe1e0"
typography:
  display:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "1.85rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "0.01em"
  body:
    fontFamily: "Source Sans 3, Segoe UI, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "IBM Plex Mono, SFMono-Regular, Consolas, monospace"
    fontSize: "0.68rem"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "0.06em"
rounded:
  sm: "0"
  md: "0"
  lg: "0"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    padding: "9px 16px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "9px 16px"
  button-danger:
    backgroundColor: "transparent"
    textColor: "{colors.status-error}"
    rounded: "{rounded.sm}"
    padding: "9px 16px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "20px"
  badge:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    rounded: "0"
    padding: "3px 8px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
---

# Design System: TransTooLing

## Overview

**Creative North Star: "L'atelier qui prend racine"**

TransTooLing adopte la charte éditoriale de radixhomework.github.io : un
atelier personnel aux couleurs de terre — noir racine, ivoire, vert mousse,
cuivre patiné — posé sur des surfaces de papier chaud. La typographie mène :
Cormorant Garamond porte les titres en capitales espacées, comme le fronton
d'un atelier ; Source Sans 3 porte les phrases ; IBM Plex Mono reste la voix
discrète des données (identifiants, modèles, tailles, dates). Le logo —
emblème sombre cerclé — remplace l'ancienne marque à barres dans l'en-tête,
la page de connexion et le favicon.

Le langage est éditorial et plat : angles droits partout, aucune ombre, des
bordures fines noir racine semi-transparentes pour séparer les surfaces. La
couleur est rare — le vert mousse pour agir, le cuivre pour les attentes et
les survols de liens, le rose fané pour les erreurs. La forme d'onde reste
le seul indicateur animé de traitement.

**Key Characteristics:**
- Charte radixhomework : noir racine, ivoire, vert mousse, cuivre patiné, rose fané, parchemin
- Cormorant Garamond en capitales espacées pour titres, marque et navigation ; Source Sans 3 pour le corps
- Angles droits partout, aucune ombre : la séparation se fait par bordures fines
- Logo emblème (logo-96/64/32.png) dans l'en-tête, la connexion et le favicon
- IBM Plex Mono reste la voix des données ; la forme d'onde reste l'indicateur de traitement

## Colors

Palette de terre de la charte radixhomework : deux papiers, un noir racine,
trois accents naturels (mousse, cuivre, rose fané) et un parchemin de
profondeur.

### Primary
- **Vert mousse** (#4D5947) : la couleur d'action — boutons primaires,
  liens, état actif de navigation, focus, forme d'onde, statut « terminé ».
- **Vert mousse profond** (#3F4A3B) : unique variante, au survol du bouton primaire.
- **Vert mousse voilé** (#e3e7dd) : fond des badges et fonds doux verts.

### Secondary
- **Cuivre patiné** (#9A7656) : accent secondaire — statut « en attente /
  en cours / annulation », survol des liens. Avec son voile (#efe6dc).

### Tertiary
- **Rose fané** (#8A5E61) : erreurs et actions destructrices, avec son
  voile (#efe1e0).

### Neutral
- **Papier** (#fcfcfa) : fond de page.
- **Ivoire** (#fdfaf3) : surface des cartes, en-tête, champs.
- **Parchemin** (#d8d0bd) et sa demi-teinte (#eae5d8) : surfaces enfoncées,
  pistes de progression, onglets inactifs, textes préformatés.
- **Noir racine** (#1E211C) : texte principal ; ses bordures
  semi-transparentes (20 % / 40 %) séparent toutes les surfaces.
- **Brun terre** (#76604E) : texte secondaire.
- **Brun pâle** (#a18f7c) : métadonnées, légendes.

### Named Rules
**La règle de la couleur rare.** Le vert mousse couvre au plus ~10 % d'un
écran ; le cuivre et le rose fané ne sont que des états. Rien de décoratif.

## Typography

**Display Font:** Cormorant Garamond (Georgia, serif)
**Body Font:** Source Sans 3 (Segoe UI, sans-serif)
**Label/Mono Font:** IBM Plex Mono (SFMono-Regular, Consolas, monospace)

**Character:** Un garamond contemporain en capitales espacées pour le
fronton, un sans humaniste pour le travail quotidien, un mono sobre pour
les mesures — l'atelier et son registre.

### Hierarchy
- **Display** (600, 1,85 rem, 1,15) : titre unique de chaque page (h1) ;
  2 rem en capitales espacées (0,06 em) sur la page de connexion ; marque
  en-tête en 1,15 rem capitales (0,08 em).
- **Body** (400, 0,95 rem, 1,6) : paragraphes, descriptions, formulaires.
- **Label** (600, 0,72–0,78 rem, letter-spacing 0,06–0,08 em, MAJUSCULES) :
  boutons, navigation, en-têtes de tableaux, libellés de champs — la
  voix « registre » de la charte, en Source Sans 3.
- **Data** (500, 0,68–0,72 rem, letter-spacing 0,06 em, MAJUSCULES) : badges
  et valeurs techniques, en IBM Plex Mono.

### Named Rules
**La règle des deux voix.** Toute valeur mesurable ou technique (nom de
modèle, identifiant, timestamp, taille) passe en IBM Plex Mono ; toute
phrase passe en Source Sans 3. Jamais l'inverse.

## Layout

Coque applicative inchangée : en-tête sticky (64 px, ivoire, bord inférieur)
avec logo + marque + navigation + compte ; contenu centré (max-width
1040 px, padding 40 px 24 px 80 px) ; colonnes flex au rythme de 24 px ;
grilles de cartes en auto-fill minmax(220 px, 1 fr). Sous 720 px, l'en-tête
s'enveloppe et la navigation défile horizontalement. La navigation est
désormais textuelle : capitales espacées, soulignement bas à l'état actif —
plus de pastilles de fond.

## Elevation & Depth

**Totalement plat.** Aucune ombre n'existe dans le système ; la profondeur
vient du contraste papier/ivoire/parchemin et de bordures fines noir
racine semi-transparentes. Les états ne soulèvent jamais rien.

### Named Rules
**La règle du plat absolu.** Interdiction d'ajouter une ombre, un dégradé
d'état ou une élévation ; les états passent par la couleur (bord, texte,
fond voilé), toujours en 0,2 s.

## Shapes

Angles droits partout (rayons 0) — le seul arrondi résiduel est invisible
(2 px sur les barres 3 px de la forme d'onde). Les badges sont des étiquettes
carrées à filet invisible, pas des pilules. La géométrie signature est le
cercle de l'emblème-logo, contraste délibéré dans un monde d'angles droits.

## Components

### Buttons
- **Shape:** angles droits
- **Primary:** vert mousse plein, texte ivoire, capitales espacées 0,78 rem
  (600, 0,06 em), padding 9 px 16 px ; variante compacte 6 px 12 px
- **Hover / Focus:** vert profond (0,2 s) ; focus visible : contour 2 px
  vert mousse, décalé de 2 px
- **Secondary:** transparent, bord noir racine 40 %, texte encre ; survol :
  bord et texte vert mousse
- **Danger:** transparent, bord et texte rose fané ; survol : fond rose voilé
- **Disabled:** opacité 0,5

### Chips / Badges
- **Style:** étiquette carrée, IBM Plex Mono 0,68 rem capitales (0,06 em) ;
  fond voilé + texte coloré : mousse (terminé/actif), cuivre (attente,
  en cours, annulation), rose fané (erreur), parchemin (annulé : fond
  demi-teinte, texte brun terre)
- **Comportement:** le badge « en cours » embarque la forme d'onde sm et
  peut afficher un pourcentage (« En cours · 42 % »)

### Cards / Containers
- **Corner Style:** angles droits
- **Background:** ivoire sur papier
- **Shadow Strategy:** aucune (règle du plat absolu)
- **Border:** 1 px noir racine 20 % ; bord vert mousse sur la carte
  « par défaut » des modèles
- **Internal Padding:** 16–24 px, flex column, écart 12 px

### Inputs / Fields
- **Style:** ivoire, bord noir racine 40 %, angles droits, padding 10 px 12 px
- **Focus:** bord vert mousse (pas de halo)
- **Labels:** 0,8 rem, 600, brun terre, au-dessus du champ

### Navigation
- Liens texte en capitales espacées (0,78 rem, 600, 0,08 em) : encre au
  repos, vert mousse au survol ; actif : vert mousse + soulignement bas
  1 px ; padding 8 px 2 px

### Logo / Brand
Emblème fourni (frontend/public/logo.png, décliné en 96/64/32 px) :
marque sombre sur transparence, avec anneau. En-tête : 34 px à gauche du
nom TRANSTOOLING (Cormorant 600, 1,15 rem, 0,08 em). Page de connexion :
64 px au-dessus du titre. Favicon : 64/32 px.

### Waveform (composant signature)
Cinq barres verticales vert mousse (3 px) qui pulsent en oscillation douce
(0,9 s, ease-in-out, hauteur 25 % ↔ 100 %, décalage par barre). Trois
tailles : sm (14 px, badges), md (20 px), lg (32 px). Unique indicateur
d'attente animé ; désactivée sous prefers-reduced-motion.

### Progress bar
Piste parchemin demi-teinte (6 px) et remplissage vert mousse mis à
l'échelle horizontalement (scaleX, 0,4 s — sans reflow) ; pourcentage en
IBM Plex Mono 0,72 rem.

## Do's and Don'ts

### Do:
- **Do** garder le vert mousse minoritaire : actions, actif, terminé.
- **Do** passer toute donnée technique en IBM Plex Mono (règle des deux voix).
- **Do** séparer les surfaces par des bordures fines noir racine
  semi-transparentes, jamais par des ombres.
- **Do** utiliser le Cormorant en capitales espacées pour titres, marque et
  navigation — c'est le fronton de la charte.
- **Do** utiliser la forme d'onde comme unique indicateur d'attente animée.

### Don't:
- **Don't** introduire une ombre, un dégradé, un arrondi ou une deuxième
  couleur d'expression.
- **Don't** mettre du texte long en IBM Plex Mono — le mono est réservé aux
  valeurs courtes.
- **Don't** réintroduire les pastilles de fond dans la navigation ou des
  pilules de badge.
- **Don't** animer autre chose que la forme d'onde, le scaleX des barres de
  progression et les transitions de couleur de 0,2 s.
