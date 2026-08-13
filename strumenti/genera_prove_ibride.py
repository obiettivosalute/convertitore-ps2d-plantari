"""Serie di pacchetti ibridi, per isolare il layer che rompe l'import.

A cosa serve. Il pacchetto di CONTROLLO FORMATO -- layer originali, solo
nomi e anagrafica riscritti -- viene aperto e modellato senza problemi. Il
pacchetto di PROVA IMPORT, rigenerato per intero da noi, si ferma
all'apertura delle immagini. Il guasto sta quindi in uno dei layer che
scriviamo, ma il confronto byte a byte non basta a dire quale: le
differenze rimaste sono tutte legali come formato.

L'unico modo di saperlo e' chiederlo al software. Questo strumento parte
dal pacchetto di controllo e ne sforna una copia per ciascun layer,
sostituendo **quel solo layer** con la nostra versione. Il primo che non
si apre nomina il colpevole.

Ne esce anche un pacchetto con tutti i layer nostri, che rifa' la prova
completa con le correzioni del momento.

    py -3 strumenti\\genera_prove_ibride.py [controllo.zip prova.zip]
                                            [--solo sca,farima,completo]
                                            [--giro N]

Senza argomenti prende gli ultimi due pacchetti da data/_prova_import/. Il
risultato finisce in data/_prova_import/ibridi/.

`--solo` limita la serie ai layer indicati (`completo` e' il pacchetto con
tutti i layer nostri): utile dal secondo giro in poi, quando si prova una
correzione mirata e non serve rispedire tutto.

`--giro N` sposta l'anno di nascita e il codice d'archivio, cosi' i
pacchetti di un giro non si confondono in elenco con quelli del giro
precedente, che il tecnico ha gia' importato.

Il `.his` non viene messo alla prova: il pacchetto di controllo lo porta
gia' scritto da noi, e si apre. E' l'unico layer gia' assolto.

Esito del primo giro, 13 agosto 2026: si aprono `sca`, `ima`, `bmp` e
`obj`; non si apre `farima`. Il guasto era il verso delle righe del PNG,
capovolto rispetto al `.sca` nei file autentici, e il `pHYs` scritto a 72
dpi invece che alla scala vera della griglia.
"""

from __future__ import annotations

import io
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from config import DATA_DIR
from src.ps2d import DatiPaziente, impacchetta_invio, nome_archivio_invio
from src.ps2d.formats import scrivi_his


@dataclass
class Prova:
    """Un pacchetto della serie: cosa cambia e come si chiama il paziente."""

    layer: str | None          # estensione sostituita, None = tutta la prova
    paziente: DatiPaziente
    codice: str
    descrizione: str


SERIE = [
    Prova("sca", DatiPaziente("Ibrido", "Sca", "03.03.2000"), "IBSCA1",
          "controllo con la nostra mappa quote"),
    Prova("ima", DatiPaziente("Ibrido", "Ima", "04.04.2000"), "IBIMA1",
          "controllo con la nostra immagine 8 bit"),
    Prova("farima", DatiPaziente("Ibrido", "Farima", "05.05.2000"), "IBFAR1",
          "controllo con il nostro PNG a colori"),
    Prova("bmp", DatiPaziente("Ibrido", "Bmp", "06.06.2000"), "IBBMP1",
          "controllo con il nostro JPEG"),
    Prova("obj", DatiPaziente("Ibrido", "Obj", "07.07.2000"), "IBOBJ1",
          "controllo con la nostra mesh"),
    Prova(None, DatiPaziente("Prova", "Completa", "08.08.2000"), "TUTTI1",
          "tutti i layer nostri, nessuno originale"),
]

# Il tecnico distingue i pacchetti dall'anagrafica che compare in elenco.
# Rifacendo un giro con gli stessi nomi si sovrapporrebbero ai precedenti,
# quindi ogni giro sposta l'anno di nascita e marca il codice d'archivio.
def per_giro(prova: Prova, giro: int) -> Prova:
    if giro <= 1:
        return prova
    p = prova.paziente
    giorno, mese, anno = p.data_nascita.split(".")
    nuovo = DatiPaziente(p.nome, f"{p.cognome}{giro}",
                         f"{giorno}.{mese}.{int(anno) + giro - 1}", p.email)
    return Prova(prova.layer, nuovo, prova.codice[:-1] + str(giro),
                 prova.descrizione)


def chiave(nome: str) -> tuple[str, str]:
    """Identifica un layer a prescindere da anagrafica e marca temporale."""
    p = Path(nome)
    lato = "Links" if "_Links_" in p.name else "Rechts"
    return lato, p.suffix.lstrip(".").lower()


def apri_layer(pacchetto: Path) -> tuple[list[str], dict[tuple[str, str], bytes]]:
    """Estrae i layer dal .ps2d annidato, conservandone l'ordine."""
    with zipfile.ZipFile(pacchetto) as z:
        interni = [n for n in z.namelist() if n.lower().endswith(".ps2d")]
        if not interni:
            raise ValueError(f"{pacchetto.name}: nessun .ps2d dentro l'archivio")
        dati = z.read(interni[0])
    with zipfile.ZipFile(io.BytesIO(dati)) as z2:
        ordine = z2.namelist()
        return ordine, {chiave(n): z2.read(n) for n in ordine}


def costruisci(prova: Prova, ordine: list[str],
               controllo: dict[tuple[str, str], bytes],
               nostri: dict[tuple[str, str], bytes],
               istante: datetime, uscita: Path) -> Path:
    """Confeziona un pacchetto della serie e lo restituisce."""
    p = prova.paziente
    temporaneo = uscita / f"_his_{prova.codice}.tmp"
    scrivi_his(temporaneo, p.nome, p.cognome, p.data_nascita)
    his = temporaneo.read_bytes()
    temporaneo.unlink()

    base = nostri if prova.layer is None else controllo
    ps2d = uscita / f"{p.slug()}_{istante:%Y%m%d_%H%M%S}.ps2d"

    with zipfile.ZipFile(ps2d, "w", zipfile.ZIP_DEFLATED) as z:
        for nome in ordine:
            lato, ext = chiave(nome)
            if ext == "his":
                dati = his
            elif ext == prova.layer:
                dati = nostri[(lato, ext)]
            else:
                dati = base[(lato, ext)]
            nuovo = f"{p.slug()}_{lato}_{istante:%Y%m%d_%H%M%S}.{ext}"
            z.writestr(nuovo, dati)

    return impacchetta_invio(
        uscita / nome_archivio_invio(p, istante, prova.codice),
        ps2d, p, istante)


def ultimi_pacchetti() -> tuple[Path, Path] | None:
    """Pesca controllo e prova da data/_prova_import/, se ci sono."""
    cartella = DATA_DIR / "_prova_import"
    controllo = sorted(cartella.glob("*Controllo-Formato*.zip"))
    prova = sorted(cartella.glob("*Prova-Import*.zip"))
    if not controllo or not prova:
        return None
    return controllo[-1], prova[-1]


def main(argv: list[str]) -> int:
    giro, solo = 1, None
    resto: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] == "--giro" and i + 1 < len(argv):
            giro = int(argv[i + 1]); i += 2
        elif argv[i] == "--solo" and i + 1 < len(argv):
            solo = {s.strip().lower() for s in argv[i + 1].split(",")}; i += 2
        else:
            resto.append(argv[i]); i += 1

    if len(resto) >= 2:
        sorgenti = (Path(resto[0]), Path(resto[1]))
    else:
        trovati = ultimi_pacchetti()
        if trovati is None:
            print("Servono il pacchetto di controllo e quello di prova.")
            print(__doc__)
            return 2
        sorgenti = trovati

    controllo_zip, prova_zip = sorgenti
    for f in sorgenti:
        if not f.is_file():
            print(f"non trovo {f}")
            return 1

    print(f"controllo  {controllo_zip.name}")
    print(f"prova      {prova_zip.name}")
    print()

    ordine, controllo = apri_layer(controllo_zip)
    _, nostri = apri_layer(prova_zip)

    mancanti = set(controllo) - set(nostri)
    if mancanti:
        print(f"i due pacchetti non hanno gli stessi layer: manca {mancanti}")
        return 1

    uscita = DATA_DIR / "_prova_import" / "ibridi"
    uscita.mkdir(parents=True, exist_ok=True)

    # marche temporali distinte: due pacchetti con lo stesso istante
    # finirebbero con gli stessi nomi di file interni
    base = datetime.now()
    scelte = [per_giro(p, giro) for p in SERIE
              if solo is None or (p.layer or "completo") in solo]
    if not scelte:
        print(f"nessun pacchetto corrisponde a --solo {','.join(sorted(solo))}")
        print("valori ammessi: sca ima farima bmp obj completo")
        return 2

    prodotti: list[tuple[Prova, Path]] = []
    for i, prova in enumerate(scelte):
        percorso = costruisci(prova, ordine, controllo, nostri,
                              base + timedelta(seconds=i), uscita)
        prodotti.append((prova, percorso))
        etichetta = f"{prova.paziente.nome} {prova.paziente.cognome}".upper()
        print(f"  {etichetta:<16s} {prova.paziente.data_nascita}  "
              f"{percorso.stat().st_size:>9,} byte   {prova.descrizione}")

    print()
    print("=" * 72)
    print("SERIE PRONTA - da provare NELL'ORDINE, fermandosi al primo che non si apre")
    print("=" * 72)
    print(f"  {uscita}")
    print()
    print("Per ciascuno serve sapere solo: le immagini si aprono, si' o no.")
    print("Il primo che non si apre nomina il layer colpevole.")
    print()
    print("Se si aprono tutti e cinque gli ibridi, il guasto non e' in un")
    print("singolo layer ma nella combinazione, e allora si procede al")
    print("contrario: dalla prova completa, rimettendo un layer originale")
    print("alla volta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
