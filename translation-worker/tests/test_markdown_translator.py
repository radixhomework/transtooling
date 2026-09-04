"""Tests du traducteur Markdown : la syntaxe doit être préservée à
l'identique, seuls les textes visibles sont traduits."""

from app.translators import translate_markdown_content


def upper_batch(texts):
    return [t.upper() for t in texts]


def test_heading_translated_marker_preserved():
    md = "# Main title\n\n## Section deux\n"
    result = translate_markdown_content(md, upper_batch)
    assert result == "# MAIN TITLE\n\n## SECTION DEUX\n"


def test_bold_emphasis_strike_markers_preserved():
    md = "Un texte **important**, en *italique* et ~~barré~~ ici.\n"
    result = translate_markdown_content(md, upper_batch)
    assert "**" in result and "*" in result and "~~" in result
    assert "**IMPORTANT**," in result
    assert "*ITALIQUE*" in result
    assert "~~BARRÉ~~" in result


def test_inline_code_never_translated():
    md = "Utilisez la commande `sudo rm -rf` avec prudence.\n"
    result = translate_markdown_content(md, upper_batch)
    assert "`sudo rm -rf`" in result


def test_fenced_code_block_untouched():
    md = (
        "Texte avant.\n"
        "\n"
        "```python\n"
        "def hello():\n"
        "    print('Bonjour le monde')\n"
        "```\n"
        "\n"
        "Texte après.\n"
    )
    result = translate_markdown_content(md, upper_batch)
    assert "def hello():" in result
    assert "print('Bonjour le monde')" in result
    assert "```python" in result
    assert "TEXTE AVANT." in result and "TEXTE APRÈS." in result


def test_fenced_code_with_markdown_inside_untouched():
    md = "```\n# pas un titre\n**pas du gras**\n```\n"
    result = translate_markdown_content(md, upper_batch)
    assert "# pas un titre" in result
    assert "**pas du gras**" in result


def test_tilde_fence_supported():
    md = "~~~\ncode brute\n~~~\nTexte après.\n"
    result = translate_markdown_content(md, upper_batch)
    assert "code brute" in result
    assert "TEXTE APRÈS." in result


def test_blockquote_marker_preserved_inner_translated():
    md = "> Une citation **marquante** du manuel.\n"
    result = translate_markdown_content(md, upper_batch)
    assert result.startswith("> ")
    assert "UNE CITATION **MARQUANTE** DU MANUEL." in result


def test_blockquote_empty_line_preserved():
    md = ">\n> Texte cité.\n>\n"
    result = translate_markdown_content(md, upper_batch)
    assert result == ">\n> TEXTE CITÉ.\n>\n"


def test_list_markers_preserved():
    md = "- premier élément\n- deuxième élément\n  - sous-élément indenté\n1. étape une\n2. étape deux\n"
    result = translate_markdown_content(md, upper_batch)
    assert "- PREMIER ÉLÉMENT" in result
    assert "- DEUXIÈME ÉLÉMENT" in result
    assert "  - SOUS-ÉLÉMENT INDENTÉ" in result
    assert "1. ÉTAPE UNE" in result
    assert "2. ÉTAPE DEUX" in result


def test_link_label_translated_path_untouched():
    md = "Voir la [documentation officielle](https://example.com/docs?a=1) pour plus.\n"
    result = translate_markdown_content(md, upper_batch)
    assert "[DOCUMENTATION OFFICIELLE](https://example.com/docs?a=1)" in result


def test_link_with_title_part_untouched():
    md = "Le [guide complet](/fr/guide.pdf \"Télécharger le guide\") est prêt.\n"
    result = translate_markdown_content(md, upper_batch)
    assert "/fr/guide.pdf" in result
    assert "Télécharger le guide" in result  # chemin + titre intacts
    assert "[GUIDE COMPLET](" in result


def test_image_alt_translated_path_untouched():
    md = "![Logo de l'entreprise](/assets/img/logo.png)\n"
    result = translate_markdown_content(md, upper_batch)
    assert result == "![LOGO DE L'ENTREPRISE](/assets/img/logo.png)\n"


def test_escaped_characters_preserved():
    md = "Les astérisques \\*échappés\\* et le \\_underscore\\_ restent.\n"
    result = translate_markdown_content(md, upper_batch)
    assert "\\*" in result and "\\_" in result


def test_front_matter_untouched():
    md = "---\ntitle: Mon document\nlang: fr\n---\n\n# Titre traduit\n"
    result = translate_markdown_content(md, upper_batch)
    assert "title: Mon document" in result
    assert "lang: fr" in result
    assert "# TITRE TRADUIT" in result


def test_horizontal_rules_and_blank_lines_preserved():
    md = "Avant.\n\n---\n\n***\n\nAprès.\n"
    result = translate_markdown_content(md, upper_batch)
    assert "\n---\n" in result
    assert "\n***\n" in result
    assert "AVANT." in result and "APRÈS." in result


def test_nested_formatting():
    md = "**Du gras avec un *emphase* imbriquée** et du code `x=1` dedans.\n"
    result = translate_markdown_content(md, upper_batch)
    assert "**" in result and "*" in result and "`x=1`" in result
    assert "EMPHASE" in result


def test_link_inside_bold():
    md = "**Voir le [site web](https://example.com)** maintenant.\n"
    result = translate_markdown_content(md, upper_batch)
    assert "**VOIR LE [SITE WEB](https://example.com)** MAINTENANT." in result


def test_hard_break_trailing_spaces_preserved():
    md = "Ligne une.  \nLigne deux.\n"
    result = translate_markdown_content(md, upper_batch)
    assert "LIGNE UNE.  \n" in result  # deux espaces (saut de ligne Markdown)


def test_full_document():
    md = """---
title: Guide de démarrage
---

# Guide de démarrage

Bienvenue ! Ce guide explique l'installation **complète** de l'outil.

## Prérequis

- Un serveur Linux
- Docker version 20 ou supérieure
- Deux gigaoctets de mémoire

## Installation

Exécutez la commande suivante :

```bash
docker compose up -d
```

Puis ouvrez <http://localhost:8080> dans votre navigateur.

> Note : les modèles se téléchargent depuis le panneau d'administration.

![Schéma d'architecture](/img/schema.png)

Pour en savoir plus, consultez la [documentation](https://docs.example.com).
"""
    result = translate_markdown_content(md, upper_batch)
    # Structure
    assert result.startswith("---\ntitle: Guide de démarrage\n---\n")
    assert "# GUIDE DE DÉMARRAGE" in result
    assert "## PRÉREQUIS" in result and "## INSTALLATION" in result
    assert "**COMPLÈTE**" in result
    assert "- UN SERVEUR LINUX" in result
    assert "docker compose up -d" in result and "```bash" in result
    assert "<http://localhost:8080>" in result
    assert "> NOTE :" in result
    assert "![SCHÉMA D'ARCHITECTURE](/img/schema.png)" in result
    assert "[DOCUMENTATION](https://docs.example.com)" in result


def test_punctuation_only_fragments_not_translated():
    # Le « . » après le barré ne doit pas partir au modèle (sinon hallucination).
    md = "Lisez le ~~manuel ancien~~.\n"
    result = translate_markdown_content(md, upper_batch)
    assert result == "LISEZ LE ~~MANUEL ANCIEN~~.\n"


def test_trailing_punctuation_after_bold_untouched():
    md = "C'est **essentiel** !\n"
    result = translate_markdown_content(md, upper_batch)
    assert result == "C'EST **ESSENTIEL** !\n"


# --- Tableaux ---


def test_table_format_kept_cells_translated():
    md = (
        "| Étape | Description | Statut |\n"
        "| --- | --- | --- |\n"
        "| Préparation | Collecte des fichiers | Terminé |\n"
        "| Traitement | Conversion des formats | En cours |\n"
    )
    result = translate_markdown_content(md, upper_batch)
    lines = result.splitlines()
    assert lines[0] == "| ÉTAPE | DESCRIPTION | STATUT |"
    assert lines[1] == "| --- | --- | --- |"
    assert lines[2] == "| PRÉPARATION | COLLECTE DES FICHIERS | TERMINÉ |"
    assert lines[3] == "| TRAITEMENT | CONVERSION DES FORMATS | EN COURS |"


def test_table_alignment_row_preserved():
    md = (
        "| Nom | Valeur | Prix |\n"
        "| :--- | :---: | ---: |\n"
        "| abc | xyz | 12 |\n"
    )
    result = translate_markdown_content(md, upper_batch)
    lines = result.splitlines()
    assert lines[1] == "| :--- | :---: | ---: |"


def test_table_escaped_pipe_not_split():
    md = (
        "| Commande | Rôle |\n"
        "| --- | --- |\n"
        "| a \\| b | c |\n"
    )
    result = translate_markdown_content(md, upper_batch)
    lines = result.splitlines()
    # La cellule contenant un pipe échappé reste une seule cellule.
    assert lines[2].count("|") == 4  # 2 bordures + 2 séparateurs
    assert "\\|" in lines[2]


def test_table_inline_formatting_in_cells():
    md = (
        "| Fonction | Détail |\n"
        "| --- | --- |\n"
        "| **Mode strict** | Voir [la doc](/doc) |\n"
    )
    result = translate_markdown_content(md, upper_batch)
    assert "**MODE STRICT**" in result
    assert "[LA DOC](/doc)" in result


def test_table_ends_at_plain_line():
    md = (
        "| A | B |\n"
        "| --- | --- |\n"
        "| un | deux |\n"
        "\n"
        "Paragraphe suivant la table.\n"
    )
    result = translate_markdown_content(md, upper_batch)
    assert "PARAGRAPHE SUIVANT LA TABLE." in result
    lines = result.splitlines()
    assert lines[2].startswith("| UN")


def test_table_without_border_pipes():
    md = (
        "Titre un | Titre deux\n"
        "--- | ---\n"
        "Valeur un | Valeur deux\n"
    )
    result = translate_markdown_content(md, upper_batch)
    lines = result.splitlines()
    assert lines[0] == "TITRE UN | TITRE DEUX"
    assert lines[1] == "--- | ---"
    assert lines[2] == "VALEUR UN | VALEUR DEUX"
