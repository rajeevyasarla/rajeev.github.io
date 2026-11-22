"""Read-only content, HTML, local asset, citation, and public-CV checks."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.ids = set()
        self.urls = []
        self.scripts = []
        self.json_script = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            assert attrs["id"] not in self.ids, f"Duplicate ID: {attrs['id']}"
            self.ids.add(attrs["id"])
        for key in ("href", "src", "poster"):
            if attrs.get(key):
                self.urls.append(attrs[key])
        if tag == "a" and attrs.get("target") == "_blank":
            assert {"noopener", "noreferrer"} <= set(attrs.get("rel", "").split())
        if tag == "img":
            assert attrs.get("alt"), "Image lacks descriptive alt text"
        if tag == "script":
            self.json_script = attrs.get("type") == "application/ld+json"
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        assert self.stack and self.stack[-1] == tag, f"Unbalanced HTML tag: {tag}"
        self.stack.pop()
        if tag == "script":
            self.json_script = False

    def handle_data(self, data):
        if self.json_script:
            self.scripts.append(json.loads(data))


def local_asset(url, ids=None):
    parts = urlsplit(url)
    assert parts.scheme in ("", "http", "https", "mailto"), f"Unsafe URL: {url}"
    if parts.scheme or parts.netloc:
        return
    if not parts.path:
        if ids is not None and parts.fragment:
            assert parts.fragment in ids, f"Missing anchor: {url}"
        return
    target = (ROOT / unquote(parts.path)).resolve()
    assert ROOT in target.parents, f"Local URL escapes the site: {url}"
    assert target.is_file(), f"Missing local asset: {url}"


html = (ROOT / "index.html").read_text()
document = Document()
document.feed(html)
assert not document.stack, f"Unclosed HTML: {document.stack}"
assert {"research", "news-list", "teaching", "publications", "projects", "service",
        "main-content", "page-top"} <= document.ids
for url in document.urls:
    local_asset(url, document.ids)
for url in re.findall(r"background-image:url\('([^']+)'\)", html):
    local_asset(url)
assert "Senior" not in html
for filename in ("index.html", "publications.json", "README.md", "files/CV.tex"):
    content = (ROOT / filename).read_text()
    assert not re.search(r"github_pat_|ghp_[A-Za-z0-9]{20,}", content), "Credential in public site content"
assert "I am a Staff Researcher" in html
assert document.scripts[0]["jobTitle"] == "Staff Researcher"
assert "calibrated transfer" not in html
assert "My goal as an educator is to help students become independent technical thinkers" not in html
assert "My mentoring model centers on clarity, evidence, and independence" not in html
assert "NeurIPS 2025, CES 2026, and CVPR 2026" in html
assert not re.search(r"<strong>(?:EN\.520\.344|EE4371|EE1100)</strong>", html)
projects = ["I led MAMo (ICCV 2023)", "FutureDepth (ECCV 2024)",
            "DiMA, CVPR 2025", "RoCA (ICML 2026)", "GeRo (NeurIPS 2026)",
            "MAPLE (NeurIPS 2026)"]
positions = [html.index(name) for name in projects]
assert positions == sorted(positions), "Project leadership list is not chronological"

demo = ROOT / "img/assets/MAPLE/MAPLE_vs_DeepSight_3x2.mp4"
demo_manifest = json.loads(demo.with_suffix(".json").read_text())
demo_info = json.loads(subprocess.check_output([
    "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(demo)
], text=True))
demo_video = next(stream for stream in demo_info["streams"] if stream["codec_type"] == "video")
assert float(demo_info["format"]["duration"]) == 20 and demo_manifest["duration_seconds"] == 20
assert demo_video["codec_name"] == "h264" and demo_video["pix_fmt"] == "yuv420p"
assert (demo_video["width"], demo_video["height"]) == (1920, 1620)
assert int(demo_video["nb_frames"]) == 240
assert demo_manifest["grid_rows"] == 3 and demo_manifest["grid_columns"] == 2
assert demo_manifest["method_columns"] == ["MAPLE", "DeepSight"]
assert not any(stream["codec_type"] == "audio" for stream in demo_info["streams"])
assert demo.stat().st_size < 20 * 1024 * 1024
assert demo_manifest["same_elapsed_simulation_time_per_method_pair"] and demo_manifest["playback_speed_vs_simulation"] == 2
assert len(demo_manifest["source_segments"]) == 3
assert hashlib.sha256(demo.read_bytes()).hexdigest() == demo_manifest["video_sha256"]
assert hashlib.sha256(demo.with_suffix(".jpg").read_bytes()).hexdigest() == demo_manifest["poster_sha256"]
assert [segment["output_end_seconds"] - segment["output_start_seconds"]
        for segment in demo_manifest["source_segments"]] == [20, 20, 20]
assert [segment["grid_row"] for segment in demo_manifest["source_segments"]] == [1, 2, 3]
assert all(segment["output_start_seconds"] == 0 for segment in demo_manifest["source_segments"])
assert 'preload="none" poster="img/assets/MAPLE/MAPLE_vs_DeepSight_3x2.jpg"' in html
assert 'src="img/assets/MAPLE/MAPLE_vs_DeepSight_3x2.mp4" type="video/mp4"' in html
assert "ORION with and without RoCA" in html
assert "ORION + RoCA (left) with the ORION baseline without RoCA (right)" in html
assert 'poster="img/assets/RoCA/RoCA_vs_ORION_3x2.jpg" width="1920" height="1620"' in html

news = re.search(r'<section id="news-list"[^>]*>.*?</section>', html, re.S).group(0)
entries = re.findall(r'<li class="row mb-2">.*?</li>', news, re.S)
months = {name: index for index, name in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
news_dates = []
for entry in entries:
    match = re.search(r'news-date">([A-Z][a-z]{2}) (\d{4})</div>', entry)
    assert match, "News entries must have a confirmed month and year"
    news_dates.append((int(match[2]), months[match[1]]))
assert news_dates == sorted(news_dates, reverse=True), "News must be newest first"
for marker, date in (
    ("Promoted to", "Nov 2026"),
    ("Safe and Defensive Autonomous Driving Workshop", "Sep 2026"),
    ("Area Chair for WACV 2027", "Jul 2026"),
    ("<em>RoCA</em>", "Jul 2026"),
):
    entry = next(entry for entry in entries if marker in entry)
    assert f'news-date">{date}</div>' in entry, f"Incorrect date for {marker}"

pubs = json.loads((ROOT / "publications.json").read_text())
assert len(pubs) == 14
assert [p["year"] for p in pubs] == sorted([p["year"] for p in pubs], reverse=True)
assert pubs[0]["title"].startswith("MAPLE")
assert len({p["title"] for p in pubs}) == len(pubs)
keys = []
for pub in pubs:
    assert pub["authors"] and pub["title"] and pub["venue"]
    assert pub["image_alt"]
    local_asset(pub["image"])
    assert not re.search(r"<(?!/?strong>)", pub["authors_html"]), "Unexpected author HTML"
    for url in pub["links"].values():
        local_asset(url)
    bib = (ROOT / pub["links"]["bibtex"]).read_text()
    key = re.search(r"@\w+\{([^,]+),", bib).group(1)
    keys.append(key)
assert len(keys) == len(set(keys)), "Duplicate BibTeX keys"
expected = {
    "MAPLE:": ("2605.14201v3", "Hanno Ackermann", "Pranav Desai"),
    "Generative Scenario": ("2601.11475v2", "Mohammad Ghavamzadeh"),
    "RoCA:": ("2506.10145v3", "Apratim Bhattacharyya, Shweta Mahajan, Litian Liu"),
}
for prefix, (version, *authors) in expected.items():
    pub = next(p for p in pubs if p["title"].startswith(prefix))
    assert version in pub["links"]["pdf"]
    for author in authors:
        assert author in pub["authors"]
    assert version in (ROOT / pub["links"]["bibtex"]).read_text()

cv = ROOT / "files/CV.pdf"
info = subprocess.check_output(["pdfinfo", str(cv)], text=True)
assert re.search(r"Pages:\s+5\b", info), "Public CV should retain five pages"
text = subprocess.check_output(["pdftotext", str(cv), "-"], text=True)
assert "Staff Researcher" in text and "Senior" not in text
assert "October 30, 2026" in text, "Citation statistics must remain explicitly dated"
assert "REFERENCES" not in text
for email in ("vpatel36@jhu.edu", "rchella4@jhu.edu", "cep@jhu.edu"):
    assert email not in text, "Private referee delivery details in public CV"
for version in ("2605.14201v3", "2601.11475v2", "2506.10145v3"):
    assert version in (ROOT / "files/CV.tex").read_text()
assert not re.search(r"Overfull|Missing character|Undefined control sequence",
                     (ROOT / "files/CV.log").read_text())
print("PASS: balanced HTML, metadata, all local assets/anchors, 14 publications,")
print("updated paper versions/authors, unique BibTeX keys, chronological projects,")
print("confirmed news dates/order, requested teaching removals, unbolded course names,")
print("20-second 3x2 synchronized MAPLE demo, and five-page public Staff Researcher CV.")
