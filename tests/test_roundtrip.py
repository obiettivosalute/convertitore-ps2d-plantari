"""Verifica il generatore rigenerando un pacchetto da una scansione reale.

Prende l'OBJ estratto da un .ps2d autentico, lo tratta come se fosse un
modello caricato dall'utente e ricostruisce il pacchetto. Poi confronta il
risultato con l'originale: header, dimensioni della griglia, escursione
verticale e correlazione punto per punto della mappa quote.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from src.ps2d import (DatiPaziente, carica_mesh, controlla_plausibilita,
                      converti, descrivi, impacchetta_invio, impacchetta_ps2d,
                      leggi_ps2d, nome_archivio_invio, quantizza, scrivi_lato)


def confronta_mappe(a: np.ndarray, ma: np.ndarray,
                    b: np.ndarray, mb: np.ndarray) -> dict:
    """Correlazione fra due mappe quote allineate al meglio."""
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    migliore = {"r": 0.0, "dy": 0, "dx": 0, "n": 0}
    for dy in range(-30, 31, 5):
        for dx in range(-30, 31, 5):
            A = np.roll(np.roll(a[:h, :w], dy, 0), dx, 1)
            MA = np.roll(np.roll(ma[:h, :w], dy, 0), dx, 1)
            m = MA & mb[:h, :w]
            if m.sum() < 2000:
                continue
            r = float(np.corrcoef(A[m], b[:h, :w][m])[0, 1])
            if abs(r) > abs(migliore["r"]):
                migliore = {"r": r, "dy": dy, "dx": dx, "n": int(m.sum())}
    return migliore


def main(sorgente_obj: Path, originale_ps2d: Path, uscita: Path) -> int:
    print("=" * 72)
    print("ORIGINALE")
    print("=" * 72)
    orig = leggi_ps2d(originale_ps2d)
    print(descrivi(orig))

    print()
    print("=" * 72)
    print("RIGENERAZIONE a partire da", sorgente_obj.name)
    print("=" * 72)

    mesh = carica_mesh(sorgente_obj)
    ris = converti(mesh, mm_per_px=0.5, frame=(340, 684), superficie="superiore")
    print(f"  assi: verticale={ris.asse_verticale}  "
          f"ingombro {ris.lunghezza_mm:.1f} x {ris.larghezza_mm:.1f} x {ris.altezza_mm:.1f} mm")
    print(f"  celle valide: {int(ris.maschera.sum())}  area {ris.area_cm2:.1f} cm2")
    for a in ris.avvisi:
        print(f"  avviso: {a}")
    for a in controlla_plausibilita(ris):
        print(f"  controllo: {a}")

    valori, mm_unita = quantizza(ris)
    print(f"  quantizzazione: {mm_unita:.9f} mm per unita "
          f"(fondo scala {mm_unita*65535:.2f} mm)")

    paziente = DatiPaziente("Anna", "Verdi", "04.11.1982", "test@test.com")
    istante = datetime(2026, 7, 1, 9, 40, 5)
    uscita.mkdir(parents=True, exist_ok=True)
    prodotti = scrivi_lato(uscita, paziente, "Links", ris.quote_mm, ris.maschera,
                           0.5, mm_unita, valori, istante)
    for p in prodotti:
        print(f"  scritto {p.name:60s} {p.stat().st_size:>9,} byte")

    ps2d = impacchetta_ps2d(uscita / f"{paziente.slug()}_{istante:%Y%m%d_%H%M%S}.ps2d",
                            prodotti)
    zip_invio = impacchetta_invio(
        uscita / nome_archivio_invio(paziente, istante, "0AD9FF"), ps2d,
        paziente, istante)
    print(f"  pacchetto  {ps2d.name}  {ps2d.stat().st_size:,} byte")
    print(f"  invio      {zip_invio.name}  {zip_invio.stat().st_size:,} byte")

    print()
    print("=" * 72)
    print("RILETTURA DEL PACCHETTO GENERATO")
    print("=" * 72)
    nuovo = leggi_ps2d(zip_invio)
    print(descrivi(nuovo))

    print()
    print("=" * 72)
    print("CONFRONTO")
    print("=" * 72)
    o = orig.lati["Links"]
    n = nuovo.lati["Links"]
    print(f"  griglia    originale {o.larghezza}x{o.altezza}   generata {n.larghezza}x{n.altezza}")
    print(f"  mm/px      originale {o.mm_per_px}          generata {n.mm_per_px}")
    print(f"  escursione originale {o.escursione_mm:.2f} mm   generata {n.escursione_mm:.2f} mm")
    print(f"  area       originale {o.area_cm2:.1f} cm2      generata {n.area_cm2:.1f} cm2")
    c = confronta_mappe(n.quote_mm, n.maschera, o.quote_mm, o.maschera)
    print(f"  correlazione mappe quote: r={c['r']:+.4f} "
          f"(scarto {c['dy']},{c['dx']} px su {c['n']} celle)")
    # la mesh di partenza e' quella dello scanner, gia' sottocampionata a 3 mm:
    # oltre questa soglia non si puo' andare, il dato di riferimento e' piu'
    # grossolano della griglia su cui lo si riproietta
    esito = abs(c["r"]) > 0.95
    print()
    print("ESITO:", "conforme" if esito else "DIFFORME — controllare")
    return 0 if esito else 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("uso: test_roundtrip.py <cartella_layer_estratti> <pacchetto_originale>")
        raise SystemExit(2)
    obj = next(Path(sys.argv[1]).glob("*_Links_*.obj"))
    orig = Path(sys.argv[2])
    raise SystemExit(main(obj, orig, RADICE / "data" / "_test_roundtrip"))
