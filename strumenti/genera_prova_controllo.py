"""Pacchetto di controllo: l'originale con la sola anagrafica cambiata.

A cosa serve. Se un pacchetto generato da noi non viene aperto, resta da
capire se il problema sia nei dati che scriviamo o nel modo in cui il
pacchetto e' confezionato: nomi dei file, anagrafica, struttura degli ZIP.

Questo strumento costruisce un pacchetto in cui **i layer sono i byte
originali, non toccati**: cambiano solo i nomi dei file e il contenuto del
`.his`. Se il software lo apre, l'involucro e' fuori discussione e il
problema sta nei layer che generiamo. Se non lo apre nemmeno, il problema e'
a monte, nel confezionamento o nell'anagrafica.

    py -3 strumenti\\genera_prova_controllo.py <pacchetto_originale.ps2d>

Il risultato finisce in data/_prova_import/.
"""

from __future__ import annotations

import io
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from config import DATA_DIR
from src.ps2d import DatiPaziente, impacchetta_invio
from src.ps2d.formats import scrivi_his

PAZIENTE = DatiPaziente("Controllo", "Formato", "02.02.2000", "prova@example.com")


def rinomina(vecchio: str, istante: datetime) -> str:
    """Sostituisce anagrafica e marca temporale, lasciando lato ed estensione."""
    p = Path(vecchio)
    lato = "Links" if "_Links_" in p.name else "Rechts"
    return f"{PAZIENTE.slug()}_{lato}_{istante:%Y%m%d_%H%M%S}{p.suffix}"


def main(sorgente: Path) -> int:
    istante = datetime.now()
    uscita = DATA_DIR / "_prova_import"
    uscita.mkdir(parents=True, exist_ok=True)

    if not zipfile.is_zipfile(sorgente):
        print(f"{sorgente.name} non e' un pacchetto valido")
        return 1

    # .his nuovo, scritto con lo stesso strumento del generatore
    temporaneo = uscita / "_his_controllo.tmp"
    scrivi_his(temporaneo, PAZIENTE.nome, PAZIENTE.cognome, PAZIENTE.data_nascita)
    his = temporaneo.read_bytes()
    temporaneo.unlink()

    nome_ps2d = f"{PAZIENTE.slug()}_{istante:%Y%m%d_%H%M%S}.ps2d"
    destinazione = uscita / nome_ps2d

    with zipfile.ZipFile(sorgente) as origine:
        ordine = origine.namelist()
        with zipfile.ZipFile(destinazione, "w", zipfile.ZIP_DEFLATED) as nuovo:
            for nome in ordine:
                dati = origine.read(nome)
                nuovo_nome = rinomina(nome, istante)
                if nome.lower().endswith(".his"):
                    dati = his
                    nota = "sostituito"
                else:
                    nota = "invariato, byte originali"
                nuovo.writestr(nuovo_nome, dati)
                print(f"  {nuovo_nome:58s} {len(dati):>9,} byte  {nota}")

    zip_invio = impacchetta_invio(
        uscita / (f"Obiettivo Salute_{PAZIENTE.nome}-{PAZIENTE.cognome}_-"
                  f"{PAZIENTE.data_nascita}-{istante:%d.%m.%Y}-CTRL01.zip"),
        destinazione, PAZIENTE, istante)

    print()
    print("=" * 68)
    print("PACCHETTO DI CONTROLLO PRONTO")
    print("=" * 68)
    print(f"  {zip_invio}")
    print()
    print("Paziente: CONTROLLO FORMATO, nato 02.02.2000")
    print()
    print("I layer sono quelli originali, byte per byte: cambiano solo i nomi")
    print("dei file e l'anagrafica. Se questo si apre e l'altro no, il")
    print("problema e' nei dati che generiamo. Se non si apre nemmeno questo,")
    print("il problema e' nel confezionamento o nell'anagrafica.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(Path(sys.argv[1])))
