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

# Librerie richieste, come (nome da importare, nome da installare).
LIBRERIE = (("numpy", "numpy"), ("scipy", "scipy"), ("PIL", "Pillow"),
            ("trimesh", "trimesh"), ("PyQt6", "PyQt6"))


def importabile(modulo: str) -> bool:
    try:
        __import__(modulo)
    except ImportError:
        return False
    return True


def librerie_mancanti() -> list[str]:
    """Pacchetti da installare, fra quelli che servono al gestionale."""
    return [pacchetto for modulo, pacchetto in LIBRERIE
            if not importabile(modulo)]


def avvisa_librerie(mancanti: list[str]) -> None:
    """Comunica quali librerie mancano, console o non console.

    Con il doppio clic l'applicazione parte sotto pythonw.exe, che non ha
    finestra di testo: quello che si stampa non lo legge nessuno e sembra
    semplicemente che non succeda niente. Se PyQt6 c'e' — e manca solo
    qualcos'altro — l'avviso passa quindi da una finestra di dialogo.
    """
    testo = ("Mancano queste librerie:\n\n  "
             + "\n  ".join(mancanti)
             + "\n\nPer installarle, da un prompt dei comandi:\n\n"
             + "  py -3 -m pip install " + " ".join(mancanti))
    print(testo)

    if not importabile("PyQt6"):
        return
    from PyQt6.QtWidgets import QApplication, QMessageBox

    from config import APP_NOME
    applicazione = QApplication.instance() or QApplication(sys.argv)
    QMessageBox.critical(None, f"{APP_NOME} — librerie mancanti", testo)


def controlla_ambiente() -> int:
    """Verifica che le librerie necessarie siano installate."""
    mancanti: list[str] = []
    for modulo, pacchetto in LIBRERIE:
        if importabile(modulo):
            print(f"  {pacchetto:12s} presente")
        else:
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

    # Il controllo va fatto qui, prima di toccare src.gui: da li' in avanti
    # la catena di import arriva a scipy e trimesh, e senza di loro l'avvio
    # muore con un traceback che non dice all'utente cosa fare.
    mancanti = librerie_mancanti()
    if mancanti:
        avvisa_librerie(mancanti)
        return 1

    from PyQt6.QtWidgets import QApplication

    from config import APP_NOME
    from src.gui import FinestraPrincipale

    applicazione = QApplication(sys.argv)
    applicazione.setApplicationName(APP_NOME)
    finestra = FinestraPrincipale()
    finestra.show()
    return applicazione.exec()


if __name__ == "__main__":
    raise SystemExit(main())
