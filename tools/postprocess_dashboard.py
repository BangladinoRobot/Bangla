from pathlib import Path

BASE_DIRS = [
    Path("ildottorpalinsesto"),
    Path("docs/ildottorpalinsesto"),
]

PLACEHOLDER = (
    '<p class="empty">Elenco spostato nella pagina dedicata: '
    '<a href="campionati.html#metodo-00migliorato">VEDI ELENCO</a></p>'
)

def strip_leagues_list_from_home(html: str) -> str:
    needle = "<h3>Campionati analizzati</h3>"
    i = html.find(needle)
    if i == -1:
        return html  # niente da fare

    # trova la prima <ul ...> dopo il titolo
    ul_start = html.find("<ul", i)
    if ul_start == -1:
        return html

    ul_end = html.find("</ul>", ul_start)
    if ul_end == -1:
        return html

    ul_end += len("</ul>")
    return html[:ul_start] + PLACEHOLDER + html[ul_end:]


def process_folder(folder: Path):
    idx = folder / "index.html"
    if not idx.exists():
        return

    original = idx.read_text(encoding="utf-8")

    # 1) pagina campionati = versione completa (con lista)
    camp = folder / "campionati.html"
    camp.write_text(original, encoding="utf-8")

    # 2) home = versione pulita (senza lista)
    cleaned = strip_leagues_list_from_home(original)
    idx.write_text(cleaned, encoding="utf-8")

    print(f"OK: {idx} (pulita) + {camp} (lista)")

def main():
    for d in BASE_DIRS:
        process_folder(d)

if __name__ == "__main__":
    main()
