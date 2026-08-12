"""Gestionale plantari — avvio dell'applicazione.

    python main.py              apre l'interfaccia grafica
    python main.py --controlla  verifica l'ambiente ed esce
    python main.py --ispeziona <file.ps2d>   stampa il contenuto di un pacchetto
"""

from __future__ import annotations

import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))


def controlla_ambiente() -> int:
    """Verifica che le librerie necessarie siano installate."""
    mancanti: list[str] = []
    for modulo, pacchetto in (("numpy", "numpy"), ("scipy", "scipy"),
                              ("PIL", "Pillow"), ("trimesh", "trimesh"),
                              ("PyQt6", "PyQt6")):
        try:
            __import__(modulo)
            print(f"  {pacchetto:12s} presente")
        except ImportError:
            print(f"  {pacchetto:12s} MANCANTE")
            mancanti.append(pacchetto)

    from config import DATA_DIR
    print(f"\n  archivio dati: {DATA_DIR}")

    if mancanti:
        print("\nInstalla le librerie mancanti con:")
        print("  py -3 -m pip install " + " ".join(mancanti))
        return 1
    print("\nAmbiente a posto.")
    return 0


def ispeziona(percorso: str) -> int:
    from src.ps2d import descrivi, leggi_ps2d
    try:
        print(descrivi(leggi_ps2d(percorso)))
    except Exception as exc:
        print(f"lettura non riuscita: {exc}")
        return 1
    return 0


def main() -> int:
    if "--controlla" in sys.argv:
        return controlla_ambiente()
    if "--ispeziona" in sys.argv:
        i = sys.argv.index("--ispeziona")
        if i + 1 >= len(sys.argv):
            print("uso: python main.py --ispeziona <file.ps2d>")
            return 2
        return ispeziona(sys.argv[i + 1])

    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print("PyQt6 non è installato. Esegui:  py -3 -m pip install PyQt6")
        return 1

    from config import APP_NOME
    from src.gui import FinestraPrincipale

    applicazione = QApplication(sys.argv)
    applicazione.setApplicationName(APP_NOME)
    finestra = FinestraPrincipale()
    finestra.show()
    return applicazione.exec()


if __name__ == "__main__":
    raise SystemExit(main())
