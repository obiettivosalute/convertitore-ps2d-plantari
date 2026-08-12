"""Misura l'errore introdotto dalla conversione mesh -> mappa quote.

Due prove indipendenti:

1. superficie analitica: si costruisce una forma di cui si conosce l'altezza
   esatta in ogni punto, la si salva in STL e la si riconverte. Lo scarto
   rispetto alla formula dice quanto e' accurata la proiezione.

2. andata e ritorno su dati reali: si prende la mappa quote di una scansione
   autentica, la si trasforma in mesh alla piena risoluzione e la si
   riconverte. Senza sottocampionamento l'errore deve essere trascurabile.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from src.ps2d import carica_mesh, converti, quantizza
from src.ps2d.reader import leggi_ps2d


def superficie_prova(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Forma tipo plantare: cuneo longitudinale piu' bombatura dell'arco."""
    return (12.0 * np.exp(-(((x - 12.0) / 26.0) ** 2 + ((y - 95.0) / 55.0) ** 2))
            + 3.0 * np.exp(-((y - 215.0) / 40.0) ** 2)
            + 0.008 * y)


def prova_analitica(passo_mesh: float = 0.4) -> dict:
    larghezza, lunghezza = 90.0, 260.0
    xs = np.arange(0.0, larghezza + passo_mesh, passo_mesh)
    ys = np.arange(0.0, lunghezza + passo_mesh, passo_mesh)
    X, Y = np.meshgrid(xs, ys)
    Z = superficie_prova(X, Y)

    nx, ny = len(xs), len(ys)
    V = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    idx = np.arange(nx * ny).reshape(ny, nx)
    a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel()
    c = idx[1:, 1:].ravel();   d = idx[1:, :-1].ravel()
    F = np.vstack([np.column_stack([a, b, c]), np.column_stack([a, c, d])])
    mesh = trimesh.Trimesh(vertices=V, faces=F, process=False)

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "prova.stl"
        mesh.export(f)
        ricaricata = carica_mesh(f)
        ris = converti(ricaricata, mm_per_px=0.5, margine_mm=6.0, unita="mm")

    # ricostruisce le coordinate fisiche di ogni cella e confronta
    h, w = ris.quote_mm.shape
    m = ris.maschera
    yy, xx = np.nonzero(m)
    # il modello e' centrato nel fotogramma: risali all'origine
    cx = (w - 1) / 2.0
    cy = (h - 1) / 2.0
    px = (xx - cx) * 0.5 + larghezza / 2.0
    py = (yy - cy) * 0.5 + lunghezza / 2.0
    dentro = (px >= 1) & (px <= larghezza - 1) & (py >= 1) & (py <= lunghezza - 1)

    atteso = superficie_prova(px[dentro], py[dentro])
    ottenuto = ris.quote_mm[m][dentro]
    # entrambe le grandezze sono quote relative al minimo del proprio insieme
    atteso = atteso - atteso.min()
    ottenuto = ottenuto - ottenuto.min()
    err = np.abs(atteso - ottenuto)

    return {
        "celle": int(dentro.sum()),
        "errore_medio_mm": float(err.mean()),
        "errore_p99_mm": float(np.percentile(err, 99)),
        "errore_max_mm": float(err.max()),
        "escursione_mm": float(atteso.max() - atteso.min()),
        "avvisi": ris.avvisi,
    }


def prova_andata_ritorno(pacchetto: Path, lato: str = "Rechts") -> dict:
    contenuto = leggi_ps2d(pacchetto)
    v = contenuto.lati[lato]
    quote, maschera = v.quote_mm, v.maschera

    # mesh alla piena risoluzione della griglia originale
    h, w = quote.shape
    yy, xx = np.nonzero(maschera)
    indice = np.full(quote.shape, -1, dtype=np.int64)
    indice[maschera] = np.arange(len(yy))
    # i vertici vanno al centro delle celle: la conversione stima il valore
    # centrale, metterli sull'angolo introdurrebbe mezzo pixel di sfasamento
    V = np.column_stack([(xx + 0.5) * v.mm_per_px,
                         (yy + 0.5) * v.mm_per_px,
                         quote[maschera]])
    a = indice[:-1, :-1]; b = indice[:-1, 1:]
    c = indice[1:, 1:];   d = indice[1:, :-1]
    ok = (a >= 0) & (b >= 0) & (c >= 0) & (d >= 0)
    F = np.vstack([
        np.column_stack([a[ok], b[ok], c[ok]]),
        np.column_stack([a[ok], c[ok], d[ok]]),
    ])
    mesh = trimesh.Trimesh(vertices=V, faces=F, process=False)

    # centra=False: le coordinate della mesh sono gia' quelle della griglia,
    # ricentrarle sfaserebbe il confronto
    ris = converti(mesh, mm_per_px=v.mm_per_px, frame=(w, h), unita="mm",
                   centra=False)
    valori, mm_unita = quantizza(ris)

    m = ris.maschera & maschera
    A = ris.quote_mm[m] - ris.quote_mm[m].min()
    B = quote[m] - quote[m].min()
    err = np.abs(A - B)

    # Sul contorno la proiezione 2.5D ha un limite intrinseco: le pareti
    # quasi verticali, viste dall'alto, ricadono sulle celle vicine e ne
    # alzano la quota. Si misura quindi anche l'errore lontano dai bordi.
    from scipy import ndimage
    interno = ndimage.binary_erosion(maschera, iterations=3)
    mi = interno[m]
    err_interno = err[mi]

    # pendenza locale della superficie originale, in mm di dislivello per cella
    gy, gx = np.gradient(np.where(maschera, quote, np.nan).astype(np.float64))
    pendenza = np.nan_to_num(np.hypot(gx, gy))
    salto = (pendenza >= 2.0) & maschera
    # una cella e' "regolare" se e' poco inclinata e non confina con un salto:
    # le pareti quasi verticali, proiettate dall'alto, invadono le celle vicine
    vicino_a_salto = ndimage.binary_dilation(salto, iterations=3)
    regolare = (pendenza < 0.5) & maschera & ~vicino_a_salto
    dolce = regolare[m]
    ripido = salto[m]

    return {
        "lato": lato,
        "celle_confrontate": int(m.sum()),
        "celle_originale": int(maschera.sum()),
        "celle_generate": int(ris.maschera.sum()),
        "correlazione": float(np.corrcoef(A, B)[0, 1]),
        "errore_mediano_mm": float(np.median(err)),
        "errore_p99_mm": float(np.percentile(err, 99)),
        "errore_max_mm": float(err.max()),
        "interno_celle": int(mi.sum()),
        "interno_errore_medio_mm": float(err_interno.mean()),
        "interno_errore_max_mm": float(err_interno.max()),
        "regolari_pct": float(dolce.mean() * 100),
        "regolari_errore_medio_mm": float(err[dolce].mean()) if dolce.any() else 0.0,
        "regolari_errore_p999_mm": float(np.percentile(err[dolce], 99.9)) if dolce.any() else 0.0,
        "regolari_errore_max_mm": float(err[dolce].max()) if dolce.any() else 0.0,
        "salti_pct": float(ripido.mean() * 100),
        "salti_errore_medio_mm": float(err[ripido].mean()) if ripido.any() else 0.0,
        "passo_quantizzazione_mm": mm_unita,
    }


if __name__ == "__main__":
    print("=" * 72)
    print("PROVA 1 — superficie analitica nota")
    print("=" * 72)
    r1 = prova_analitica()
    for k, v in r1.items():
        print(f"  {k:22s} {v}")
    ok1 = r1["errore_max_mm"] < 0.20 and r1["errore_medio_mm"] < 0.02
    print("  esito:", "OK" if ok1 else "FUORI TOLLERANZA")

    ok2 = True
    if len(sys.argv) > 1:
        print()
        print("=" * 72)
        print("PROVA 2 — andata e ritorno su scansione reale")
        print("=" * 72)
        for lato in ("Links", "Rechts"):
            r2 = prova_andata_ritorno(Path(sys.argv[1]), lato)
            for k, v in r2.items():
                print(f"  {k:22s} {v}")
            buono = (r2["correlazione"] > 0.995
                     and r2["regolari_errore_medio_mm"] < 0.03
                     and r2["regolari_errore_p999_mm"] < 0.50)
            ok2 = ok2 and buono
            print("  esito:", "OK" if buono else "FUORI TOLLERANZA")
            print()

    raise SystemExit(0 if (ok1 and ok2) else 1)
