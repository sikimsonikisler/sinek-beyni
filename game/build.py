"""game/template.html + brain_core.js + brain_data.json -> index.html (tek dosya, çevrimdışı çalışır)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "game"
tpl = (G / "template.html").read_text(encoding="utf-8")
data = (G / "brain_data.json").read_text(encoding="utf-8")
core = (G / "brain_core.js").read_text(encoding="utf-8")
assert "/*__BRAIN_DATA__*/" in tpl and "/*__BRAIN_CORE__*/" in tpl
assert "</script" not in data + core
html = tpl.replace("/*__BRAIN_DATA__*/", "window.BRAIN_DATA = " + data + ";").replace("/*__BRAIN_CORE__*/", core)
(ROOT / "index.html").write_text(html, encoding="utf-8")
print(f"index.html yazıldı ({len(html.encode()) // 1024} KB)")
