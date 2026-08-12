"""Verifica l'isolamento dell'impronta dal piano circostante.

Il pacchetto di riferimento contiene due scansioni con difetti opposti, ed
e' per questo un banco di prova onesto: sul piede sinistro lo scanner ha
acquisito anche il piano d'appoggio, sul destro no. Il ritaglio deve
intervenire sul primo e stare fermo sul secondo.

    py -3 tests\\test_ritaglio.py <pacchetto.ps2d>
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from src.ps2d import leggi_ps2d, valuta_verso
from src.ps2d.mesh2height import RisultatoConversione
from src.ps2d.ritaglio import applica, isola_impronta, trova_piano


def misura(quote, maschera, mm_per_px):
    ys, xs = np.nonzero(maschera)
    return ((ys.max() - ys.min() + 1) * mm_per_px,
            (xs.max() - xs.min() + 1) * mm_per_px,
            maschera.sum() * mm_per_px ** 2 / 100.0)


def main(pacchetto: Path) -> int:
    contenuto = leggi_ps2d(pacchetto)
    esiti: dict[str, dict] = {}

    for lato, v in sorted(contenuto.lati.items()):
        quota, frazione = trova_piano(v.quote_mm, v.maschera)
        ritaglio = isola_impronta(v.quote_mm, v.maschera, mm_per_px=v.mm_per_px)
        dopo = applica(v.quote_mm, ritaglio)

        L0, W0, A0 = misura(v.quote_mm, v.maschera, v.mm_per_px)
        L1, W1, A1 = misura(dopo, ritaglio.maschera, v.mm_per_px)
        verso0 = valuta_verso(RisultatoConversione(
            v.quote_mm, v.maschera, v.mm_per_px, 0, 0, 0, 0, 0, "Z"))[0]
        verso1 = valuta_verso(RisultatoConversione(
            dopo, ritaglio.maschera, v.mm_per_px, 0, 0, 0, 0, 0, "Z"))[0]

        print(f"--- {lato} ---")
        print(f"  piano trovato a {quota:.1f} mm su {frazione*100:.0f}% dell'area")
        print(f"  {ritaglio.motivo}")
        print(f"  prima: {L0:.0f} x {W0:.0f} mm  {A0:.0f} cm²  verso {verso0}")
        print(f"  dopo : {L1:.0f} x {W1:.0f} mm  {A1:.0f} cm²  verso {verso1}")
        print()
        esiti[lato] = {"applicato": ritaglio.applicato, "L": L1, "W": W1,
                       "A": A1, "verso": verso1, "L0": L0}

    controlli = []
    if "Links" in esiti:
        s = esiti["Links"]
        controlli += [
            (s["applicato"], "sul sinistro il piano viene riconosciuto e tolto"),
            (240 <= s["L"] <= 270,
             f"lunghezza riportata a un valore plausibile ({s['L']:.0f} mm, era {s['L0']:.0f})"),
            (s["verso"] == "corretto",
             "dopo il ritaglio il verso diventa riconoscibile"),
        ]
    if "Rechts" in esiti:
        d = esiti["Rechts"]
        controlli += [
            (not d["applicato"],
             "sul destro, gia' pulito, il ritaglio non interviene"),
            (240 <= d["L"] <= 260, f"lunghezza invariata ({d['L']:.0f} mm)"),
        ]
    if "Links" in esiti and "Rechts" in esiti:
        scarto = abs(esiti["Links"]["L"] - esiti["Rechts"]["L"])
        controlli.append((scarto <= 15,
                          f"i due piedi tornano confrontabili (scarto {scarto:.0f} mm)"))

    tutto_bene = True
    for esatto, cosa in controlli:
        print(f"  {'OK  ' if esatto else 'NO  '} {cosa}")
        tutto_bene = tutto_bene and esatto
    return 0 if tutto_bene else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(Path(sys.argv[1])))
