"""Genera un pacchetto di prova da importare nel software di modellazione.

A cosa serve: verificare che i pacchetti prodotti da questo programma siano
accettati dal software dell'azienda fornitrice, senza rischiare nulla.

Il pacchetto viene costruito **dalla geometria di una scansione autentica**,
riletta e ripassata per intero attraverso il generatore. Se il software lo
apre come apre l'originale, il formato che generiamo e' corretto: stessa
geometria, file diverso. L'anagrafica e' di fantasia, cosi' il paziente di
prova si riconosce subito e si cancella senza confondersi con quelli veri.

    py -3 strumenti\\genera_prova_import.py <pacchetto_originale.ps2d>

Il risultato finisce in data/_prova_import/.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import trimesh

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from config import DATA_DIR
from src.ps2d import (DatiPaziente, converti, descrivi, impacchetta_invio,
                      impacchetta_ps2d, leggi_ps2d, nome_archivio_invio,
                      quantizza, scrivi_lato)

PAZIENTE = DatiPaziente("Prova", "Import", "01.01.2000", "prova@example.com")


def mesh_da_mappa(quote_mm: np.ndarray, maschera: np.ndarray,
                  mm_per_px: float) -> trimesh.Trimesh:
    """Ricostruisce una mesh alla piena risoluzione della mappa quote."""
    yy, xx = np.nonzero(maschera)
    indice = np.full(quote_mm.shape, -1, dtype=np.int64)
    indice[maschera] = np.arange(len(yy))
    V = np.column_stack([(xx + 0.5) * mm_per_px,
                         (yy + 0.5) * mm_per_px,
                         quote_mm[maschera]])
    a, b = indice[:-1, :-1], indice[:-1, 1:]
    c, d = indice[1:, 1:], indice[1:, :-1]
    ok = (a >= 0) & (b >= 0) & (c >= 0) & (d >= 0)
    F = np.vstack([np.column_stack([a[ok], b[ok], c[ok]]),
                   np.column_stack([a[ok], c[ok], d[ok]])])
    return trimesh.Trimesh(vertices=V, faces=F, process=False)


def main(sorgente: Path) -> int:
    print(f"Lettura di {sorgente.name}")
    originale = leggi_ps2d(sorgente)
    print(descrivi(originale))
    print()

    uscita = DATA_DIR / "_prova_import"
    uscita.mkdir(parents=True, exist_ok=True)
    istante = datetime.now()
    prodotti: list[Path] = []

    for lato, v in sorted(originale.lati.items()):
        if v.quote_mm is None:
            print(f"{lato}: nessuna geometria, saltato")
            continue
        print(f"{lato}: ricostruzione della mesh dalla mappa quote…")
        mesh = mesh_da_mappa(v.quote_mm, v.maschera, v.mm_per_px)
        print(f"   {len(mesh.vertices):,} vertici, {len(mesh.faces):,} facce")

        # stessa griglia dell'originale, cosi' il confronto e' diretto
        risultato = converti(mesh, mm_per_px=v.mm_per_px,
                             frame=(v.larghezza, v.altezza), unita="mm",
                             centra=False)
        valori, mm_unita = quantizza(risultato)

        m = risultato.maschera & v.maschera
        A = risultato.quote_mm[m] - risultato.quote_mm[m].min()
        B = v.quote_mm[m] - v.quote_mm[m].min()
        print(f"   scostamento dalla geometria originale: "
              f"medio {np.abs(A - B).mean():.4f} mm, "
              f"mediano {np.median(np.abs(A - B)):.4f} mm")

        prodotti += scrivi_lato(uscita, PAZIENTE, lato, risultato.quote_mm,
                                risultato.maschera, v.mm_per_px, mm_unita,
                                valori, istante)

    if not prodotti:
        print("nessun layer prodotto")
        return 1

    ps2d = impacchetta_ps2d(
        uscita / f"{PAZIENTE.slug()}_{istante:%Y%m%d_%H%M%S}.ps2d", prodotti)
    zip_invio = impacchetta_invio(
        uscita / nome_archivio_invio(PAZIENTE, istante, "PROVA1"),
        ps2d, PAZIENTE, istante)

    print()
    print("=" * 68)
    print("PACCHETTO DI PROVA PRONTO")
    print("=" * 68)
    print(f"  ZIP da importare : {zip_invio}")
    print(f"  pacchetto interno: {ps2d.name}  ({ps2d.stat().st_size:,} byte)")
    print()
    print("Come usarlo:")
    print("  1. importa questo ZIP nel software di modellazione,")
    print("     come fai con quelli che arrivano dallo scanner;")
    print("  2. il paziente si chiama PROVA IMPORT, nato 01.01.2000;")
    print("  3. controlla che le immagini si aprano e che la forma dei")
    print("     piedi sia quella giusta, non deformata ne' capovolta;")
    print("  4. a prova finita cancella il paziente.")
    print()
    print("Se si apre correttamente, il formato generato e' valido e si puo'")
    print("procedere con i modelli veri. Se da' errore, annota il messaggio")
    print("esatto: dice quale campo non gli torna.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(Path(sys.argv[1])))
