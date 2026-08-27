"""
Traducteurs de formats de fichiers pour les archives ZIP.

Chaque traducteur prend le contenu d'un fichier et une fonction
`translate_batch(texts) -> list[str]` (batch, cache géré par l'appelant), et
retourne le contenu traduit. Les clés JSON et la structure HTML sont
préservées ; seules les valeurs textuelles sont traduites.
"""

import json
import re
from html import escape, unescape
from html.parser import HTMLParser

# Attributs HTML dont la valeur est traduite (comparaison insensible à la casse).
TRANSLATABLE_ATTRS = {"alt", "title", "placeholder", "aria-label"}
# Régions dont le contenu textuel n'est PAS traduit (verbatim).
EXCLUDED_TAGS = {"script", "style", "pre", "code"}

_ENTITY_RE = re.compile(r"&(?:[a-zA-Z][a-zA-Z0-9]*|#\d+|#x[0-9a-fA-F]+);")
_PLACEHOLDER_RE = re.compile("\ue000(\\d+)\ue001")


def _encode_entities(text: str, entities: list) -> str:
    """Remplace les entités HTML par des jetons en zone d'usage privé
    (\ue000<idx>\ue001) : le moteur de traduction ne doit ni les voir ni les
    altérer."""
    def _token(match: re.Match) -> str:
        entities.append(match.group(0))
        return f"\ue000{len(entities) - 1}\ue001"

    return _ENTITY_RE.sub(_token, text)


def _decode_entities(text: str, entities: list) -> str:
    def _restore(match: re.Match) -> str:
        index = int(match.group(1))
        if 0 <= index < len(entities):
            return entities[index]
        return match.group(0)

    return _PLACEHOLDER_RE.sub(_restore, text)


# ------------------------------------------------------------------- JSON ---


def _collect_strings(node, acc: list) -> None:
    if isinstance(node, str):
        acc.append(node)
    elif isinstance(node, list):
        for item in node:
            _collect_strings(item, acc)
    elif isinstance(node, dict):
        for value in node.values():
            _collect_strings(value, acc)


def _rebuild(node, it):
    if isinstance(node, str):
        return next(it)
    if isinstance(node, list):
        return [_rebuild(item, it) for item in node]
    if isinstance(node, dict):
        # Les clés sont préservées telles quelles, seules les valeurs changent.
        return {key: _rebuild(value, it) for key, value in node.items()}
    return node  # nombres, booléens, null : inchangés


def translate_json_content(content: str, translate_batch) -> str:
    """
    Traduit les valeurs de chaînes d'un contenu JSON (clés préservées,
    listes/objets parcourus récursivement). Lève json.JSONDecodeError si le
    contenu n'est pas du JSON valide.
    """
    data = json.loads(content)
    strings: list = []
    _collect_strings(data, strings)
    translated = translate_batch(strings) if strings else []
    it = iter(translated)
    result = _rebuild(data, it)
    return json.dumps(result, ensure_ascii=False, indent=2)


# -------------------------------------------------------------------- HTML ---


class _HTMLEventParser(HTMLParser):
    """Parse le document UNE fois et produit (a) une liste d'événements
    décrivant le document, (b) la liste des textes à traduire dans l'ordre.
    Les événements « texte traduisible » portent le texte avec entités
    encodées en jetons ; le rendu décodera la traduction avec la même table
    d'entités (portée par l'instance)."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.events: list = []
        self.strings: list = []
        self._entities: list = []
        self._excluded_depth = 0
        self._buffer: list = []  # fragments ("text"|"ent", valeur)

    # -- construction des événements

    def _attrs_events(self, attrs) -> list:
        out = []
        for name, value in attrs:
            if self._excluded_depth == 0 and value and name.lower() in TRANSLATABLE_ATTRS:
                # Les entités sont décodées avant traduction puis ré-échappées
                # au rendu : le HTML reste sémantiquement équivalent.
                plain = unescape(value)
                self.strings.append(plain)
                out.append((name, True))
            else:
                out.append((name, value))
        return out

    def handle_starttag(self, tag, attrs):
        self._flush_text()
        self.events.append(("start", tag, self._attrs_events(attrs)))
        if tag in EXCLUDED_TAGS:
            self._excluded_depth += 1

    def handle_startendtag(self, tag, attrs):
        self._flush_text()
        self.events.append(("startend", tag, self._attrs_events(attrs)))

    def handle_endtag(self, tag):
        self._flush_text()
        self.events.append(("end", tag))
        if tag in EXCLUDED_TAGS and self._excluded_depth > 0:
            self._excluded_depth -= 1

    def handle_data(self, data):
        self._buffer.append(("text", data))

    def handle_entityref(self, name):
        self._buffer.append(("ent", f"&{name};"))

    def handle_charref(self, name):
        self._buffer.append(("ent", f"&#{name};"))

    def handle_comment(self, data):
        self._flush_text()
        self.events.append(("comment", data))

    def handle_decl(self, decl):
        self._flush_text()
        self.events.append(("decl", decl))

    def handle_pi(self, data):
        self._flush_text()
        self.events.append(("pi", data))

    def _flush_text(self):
        if not self._buffer:
            return
        raw = "".join(value for _, value in self._buffer)
        translatable = self._excluded_depth == 0
        encoded = _encode_entities(raw, self._entities) if translatable else None
        if translatable and encoded.strip():
            self.events.append(("text_tr", encoded))
            self.strings.append(encoded)
        else:
            # Zones exclues ou blancs/entités seuls : re-émis tels quels.
            self.events.append(("text_raw", raw))
        self._buffer = []

    def close(self):
        super().close()
        self._flush_text()


def _render_html(events: list, translations, entities: list) -> str:
    it = iter(translations)
    out = []

    for event in events:
        kind = event[0]
        if kind == "text_raw":
            out.append(event[1])
        elif kind == "text_tr":
            out.append(_decode_entities(next(it), entities))
        elif kind in ("start", "startend"):
            _, tag, attrs = event
            parts = []
            for name, value in attrs:
                if value is True:  # marqueur d'attribut traduisible
                    translated = escape(next(it), quote=True)
                    parts.append(f'{name}="{translated}"')
                elif value is None:
                    parts.append(name)
                else:
                    parts.append(f'{name}="{escape(value, quote=True)}"')
            suffix = "/>" if kind == "startend" else ">"
            out.append(f"<{tag}{' ' + ' '.join(parts) if parts else ''}{suffix}")
        elif kind == "end":
            out.append(f"</{event[1]}>")
        elif kind == "comment":
            out.append(f"<!--{event[1]}-->")
        elif kind == "decl":
            out.append(f"<!{event[1]}>")
        elif kind == "pi":
            out.append(f"<?{event[1]}>")

    return "".join(out)


def translate_html_content(content: str, translate_batch) -> str:
    """Traduit les nœuds texte et attributs configurés d'un contenu HTML,
    en excluant <script>/<style>/<pre>/<code> (contenus re-émis verbatim)."""
    parser = _HTMLEventParser()
    parser.feed(content)
    parser.close()
    translated = translate_batch(parser.strings) if parser.strings else []
    return _render_html(parser.events, translated, parser._entities)


# ----------------------------------------------------------------- Markdown ---

_MD_ESCAPE_RE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!>|~])")
_MD_INLINE_CODE_RE = re.compile(r"(`+)([\s\S]+?)\1")
_MD_AUTOLINK_RE = re.compile(r"<[A-Za-z][A-Za-z0-9+.\-]*:[^>\s]*>")
_MD_HTML_COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")
_MD_HTML_TAG_RE = re.compile(r"</?[A-Za-z][^<>]*>")
# Liens/images : [label](dest "titre") — tout le contenu des parenthèses
# (chemin, titre) est préservé tel quel, seul le libellé est traduit.
_MD_LINK_RE = re.compile(r"(!?)\[((?:[^\[\]\\]|\\.)*)\]\(([^()]*)\)")

# Étendre le gras/emphasis/barré. « _ » exige des frontières de mot pour ne
# pas casser le snake_case.
_MD_DELIMS = [
    ("**", re.compile(r"\*\*(?=\S)([\s\S]+?)(?<=\S)\*\*")),
    ("__", re.compile(r"(?<![\w\\])__(?=\S)([\s\S]+?)(?<=\S)__(?!\w)")),
    ("~~", re.compile(r"~~(?=\S)([\s\S]+?)(?<=\S)~~")),
    ("*", re.compile(r"\*(?=\S)([\s\S]+?)(?<=\S)\*")),
    ("_", re.compile(r"(?<![\w\\])_(?=\S)([\s\S]+?)(?<=\S)_(?!\w)")),
]

_MD_FENCE_RE = re.compile(r"^(\s{0,3})(`{3,}|~{3,})(.*)$")
_MD_HEADING_RE = re.compile(r"^(\s{0,3}#{1,6}\s+)(.*)$")
_MD_QUOTE_RE = re.compile(r"^(\s*>+\s?)(.*)$")
_MD_LIST_RE = re.compile(r"^(\s*(?:[-+*]|\d{1,9}[.)])\s+)(.*)$")
# Lignes décoratives : séparateurs horizontaux, soulignements setext.
_MD_DECORATION_RE = re.compile(r"^\s*[=\-_*][=\-_*\s]*$")


def _md_tokenize_inline(text: str) -> list:
    """Découpe un fragment de ligne en éléments :
    ("raw", s) syntaxe préservée verbatim, ("text", s) à traduire,
    ("delim", marqueur, éléments) gras/emphasis/barré,
    ("link", bang, éléments_libellé, parenthèses) lien ou image."""
    elements = []
    buf = []

    def flush():
        if buf:
            elements.append(("text", "".join(buf)))
            buf.clear()

    pos = 0
    while pos < len(text):
        rest = text[pos:]
        match = (
            _MD_ESCAPE_RE.match(rest)
            or _MD_INLINE_CODE_RE.match(rest)
            or _MD_AUTOLINK_RE.match(rest)
            or _MD_HTML_COMMENT_RE.match(rest)
            or _MD_HTML_TAG_RE.match(rest)
        )
        if match:
            flush()
            elements.append(("raw", match.group(0)))
            pos += match.end()
            continue
        match = _MD_LINK_RE.match(rest)
        if match:
            flush()
            bang, label, paren = match.group(1), match.group(2), match.group(3)
            elements.append(("link", bang, _md_tokenize_inline(label), paren))
            pos += match.end()
            continue
        for delim, pattern in _MD_DELIMS:
            delim_match = pattern.match(rest)
            if delim_match:
                flush()
                elements.append(("delim", delim, _md_tokenize_inline(delim_match.group(1))))
                pos += delim_match.end()
                break
        else:
            buf.append(text[pos])
            pos += 1
    flush()
    return elements


def _md_is_translatable(text: str) -> bool:
    """Un fragment sans aucune lettre ni chiffre (ponctuation seule) n'est pas
    envoyé au modèle : il serait réécrit/halluciné sans rien apporter."""
    return re.search(r"\w", text, re.UNICODE) is not None


def _md_collect_inline(elements: list, strings: list) -> None:
    for element in elements:
        kind = element[0]
        if kind == "text":
            if _md_is_translatable(element[1]):
                strings.append(element[1])
        elif kind == "delim":
            _md_collect_inline(element[2], strings)
        elif kind == "link":
            _md_collect_inline(element[2], strings)


def _md_render_inline(elements: list, translations) -> str:
    out = []
    for element in elements:
        kind = element[0]
        if kind == "raw":
            out.append(element[1])
        elif kind == "text":
            if _md_is_translatable(element[1]):
                out.append(next(translations))
            else:
                out.append(element[1])
        elif kind == "delim":
            out.append(element[1] + _md_render_inline(element[2], translations) + element[1])
        else:  # link
            _, bang, label_elements, paren = element
            out.append(
                f"{bang}[{_md_render_inline(label_elements, translations)}]({paren})"
            )
    return "".join(out)


def _md_line_element(line_body: str):
    """Élément pour le contenu d'une ligne (sans le saut de ligne) :
    préfixes de titre/citation/liste préservés, espaces de début/fin conservés."""
    match = _MD_HEADING_RE.match(line_body) or _MD_QUOTE_RE.match(line_body) or _MD_LIST_RE.match(line_body)
    if match:
        prefix, rest = match.group(1), match.group(2)
        return ("line", prefix, _md_line_element(rest), "")
    core = line_body.strip()
    leading = line_body[: len(line_body) - len(line_body.lstrip())]
    trailing = line_body[len(line_body.rstrip()):]
    if not core:
        return ("line", leading, [], trailing)
    return ("line", leading, _md_tokenize_inline(core), trailing)


def _md_collect_line(element, strings: list) -> None:
    if element[0] != "line":
        return
    nested = element[2]
    if isinstance(nested, list):
        _md_collect_inline(nested, strings)
    else:
        _md_collect_line(nested, strings)


def _md_render_line(element, translations) -> str:
    prefix, nested, trailing = element[1], element[2], element[3]
    if isinstance(nested, list):
        body = _md_render_inline(nested, translations)
    else:
        body = _md_render_line(nested, translations)
    return prefix + body + trailing


# Ligne de séparation d'un tableau GFM : uniquement | : - et espaces, avec
# au moins un tiret (ex. | --- | :---: | ---: |).
_MD_TABLE_DELIM_RE = re.compile(r"^[\s|:-]+$")
_MD_UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")


def _md_is_table_delimiter(line: str) -> bool:
    stripped = line.strip()
    return (
        bool(stripped)
        and "-" in stripped
        and "|" in stripped
        and _MD_TABLE_DELIM_RE.match(stripped) is not None
    )


def _md_cell_element(piece: str):
    """Cellule de tableau : espaces de début/fin conservés, contenu inline
    traduit (gras, liens, etc. fonctionnent dans les cellules)."""
    core = piece.strip()
    leading = piece[: len(piece) - len(piece.lstrip())]
    trailing = piece[len(piece.rstrip()):]
    return ("line", leading, _md_tokenize_inline(core) if core else [], trailing)


def _md_split_row(line: str) -> list:
    """Découpe une ligne de tableau sur les pipes non échappés ; les segments
    vides de bord (autour des pipes d'ouverture/fermeture) restent verbatim,
    les autres sont des cellules à traduire."""
    pieces = _MD_UNESCAPED_PIPE_RE.split(line)
    parts = []
    for index, piece in enumerate(pieces):
        is_border = index in (0, len(pieces) - 1) and not piece.strip()
        parts.append(("raw", piece) if is_border else ("cell", _md_cell_element(piece)))
    return parts


def _md_collect_row(parts: list, strings: list) -> None:
    for part in parts:
        if part[0] == "cell":
            _md_collect_line(part[1], strings)


def _md_render_row(parts: list, translations) -> str:
    out = []
    for part in parts:
        if part[0] == "raw":
            out.append(part[1])
        else:
            out.append(_md_render_line(part[1], translations))
    return "|".join(out)


def translate_markdown_content(content: str, translate_batch) -> str:
    """
    Traduit un document Markdown en préservant intégralement la syntaxe :
    titres, gras, italique, barré, code et blocs de code, citations, listes,
    tableaux (format et alignements conservés, contenu des cellules traduit),
    liens et images (seuls les libellés/alt sont traduits, jamais les chemins),
    caractères échappés et front matter. Seuls les textes visibles sont
    traduits.
    """
    lines = content.splitlines(keepends=True)
    elements = []  # ("raw_line", texte) | ("nested", élément) | ("table", parties)
    strings: list = []

    fence = None  # (marqueur, longueur) du bloc de code en cours
    in_front_matter = bool(lines) and lines[0].rstrip("\r\n") == "---"

    index = 0
    while index < len(lines):
        raw_line = lines[index]
        line = raw_line.rstrip("\r\n")
        newline = raw_line[len(line):]

        if in_front_matter:
            elements.append(("raw_line", raw_line))
            if index > 0 and line.strip() == "---":
                in_front_matter = False
            index += 1
            continue

        fence_match = _MD_FENCE_RE.match(line)
        if fence is not None:
            elements.append(("raw_line", raw_line))
            if fence_match and fence_match.group(2)[0] == fence[0] and len(fence_match.group(2)) >= fence[1]:
                fence = None
            index += 1
            continue
        if fence_match:
            elements.append(("raw_line", raw_line))
            fence = (fence_match.group(2)[0], len(fence_match.group(2)))
            index += 1
            continue

        if not line.strip() or _MD_DECORATION_RE.match(line):
            elements.append(("raw_line", raw_line))
            index += 1
            continue

        # Tableau GFM : ligne avec pipe suivie d'une ligne de séparation.
        if "|" in line and index + 1 < len(lines) and _md_is_table_delimiter(
            lines[index + 1].rstrip("\r\n")
        ):
            header_parts = _md_split_row(line)
            elements.append(("table", header_parts, newline))
            _md_collect_row(header_parts, strings)
            index += 1
            # Ligne de séparation (alignements) : verbatim.
            elements.append(("raw_line", lines[index]))
            index += 1
            # Lignes du corps : tant qu'elles contiennent un pipe.
            while index < len(lines):
                body_line = lines[index].rstrip("\r\n")
                if not body_line.strip() or "|" not in body_line:
                    break
                body_parts = _md_split_row(body_line)
                elements.append(("table", body_parts, lines[index][len(body_line):]))
                _md_collect_row(body_parts, strings)
                index += 1
            continue

        element = _md_line_element(line)
        elements.append(("nested", element, newline))
        _md_collect_line(element, strings)
        index += 1

    translated = iter(translate_batch(strings) if strings else [])
    out = []
    for element in elements:
        if element[0] == "raw_line":
            out.append(element[1])
        elif element[0] == "table":
            out.append(_md_render_row(element[1], translated) + element[2])
        else:
            out.append(_md_render_line(element[1], translated) + element[2])
    return "".join(out)
