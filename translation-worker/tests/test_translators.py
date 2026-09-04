import json

import pytest

from app.translators import translate_html_content, translate_json_content


def upper_batch(texts):
    return [t.upper() for t in texts]


# --- JSON ---


def test_json_translates_string_values_only():
    content = json.dumps(
        {"title": "Hello", "count": 3, "enabled": True, "nested": {"label": "World", "list": ["A", "B"]}},
        ensure_ascii=False,
    )
    result = translate_json_content(content, upper_batch)
    data = json.loads(result)
    assert data["title"] == "HELLO"
    assert data["count"] == 3
    assert data["enabled"] is True
    assert data["nested"]["label"] == "WORLD"
    assert data["nested"]["list"] == ["A", "B"]
    # Keys are never translated.
    assert "nested" in data and "label" in data["nested"]


def test_json_preserves_non_string_leaves():
    content = json.dumps({"a": None, "b": 1.5, "c": [1, 2, {"d": "text"}]})
    data = json.loads(translate_json_content(content, upper_batch))
    assert data["a"] is None
    assert data["b"] == 1.5
    assert data["c"][:2] == [1, 2]
    assert data["c"][2]["d"] == "TEXT"


def test_json_invalid_raises():
    with pytest.raises(json.JSONDecodeError):
        translate_json_content("{not json", upper_batch)


def test_json_empty_structure():
    assert json.loads(translate_json_content("{}", upper_batch)) == {}
    assert json.loads(translate_json_content("[]", upper_batch)) == []


# --- HTML ---


def test_html_translates_text_nodes_and_configured_attrs():
    html = (
        "<p>Hello world</p>"
        '<img src="x.png" alt="A cat" title="A photo">'
        '<input placeholder="Your name">'
    )
    result = translate_html_content(html, upper_batch)
    assert "HELLO WORLD" in result
    assert 'alt="A CAT"' in result
    assert 'title="A PHOTO"' in result
    assert 'placeholder="YOUR NAME"' in result
    assert 'src="x.png"' in result  # attribut non traduisible intact


def test_html_excludes_script_style_pre_code():
    html = (
        "<script>var x = 'Hello';</script>"
        "<style>p { color: red; }</style>"
        "<pre>Hello pre</pre>"
        "<code>Hello code</code>"
        "<p>Hello visible</p>"
    )
    result = translate_html_content(html, upper_batch)
    assert "var x = 'Hello';" in result
    assert "p { color: red; }" in result
    assert "Hello pre" in result
    assert "Hello code" in result
    assert "HELLO VISIBLE" in result


def test_html_preserves_entities_in_text():
    html = "<p>Caf&eacute; &amp; th&eacute;</p>"
    result = translate_html_content(html, lambda texts: [t.replace("X", "") for t in texts])
    # Entities must survive translation (private tokens restored).
    assert "&eacute;" in result
    assert "&amp;" in result
    assert "\ue000" not in result  # aucun jeton ne doit fuiter


def test_html_attrs_entities_decoded_and_escaped():
    html = '<img alt="Caf&eacute; &quot;bon&quot;">'
    result = translate_html_content(html, upper_batch)
    # Attribute value: entities decoded before translation, re-escaped after.
    assert "CAFÉ" in result
    assert "&quot;" in result or '"' in result


def test_html_structure_preserved():
    html = (
        "<!DOCTYPE html>"
        "<html><head><title>My page</title></head>"
        "<body><h1>Header</h1><!-- a comment --><br/><p>Bye</p></body></html>"
    )
    result = translate_html_content(html, upper_batch)
    assert result.startswith("<!DOCTYPE html>")
    assert "<html>" in result and "</html>" in result
    assert "<title>MY PAGE</title>" in result
    assert "<h1>HEADER</h1>" in result
    assert "<!-- a comment -->" in result
    assert "<br/>" in result
    assert "<p>BYE</p>" in result


def test_html_whitespace_only_text_nodes_untouched():
    html = "<div>\n  <span>Hello</span>\n</div>"
    result = translate_html_content(html, upper_batch)
    assert "HELLO" in result
    assert "\n  " in result  # whitespace is neither translated nor consumed
