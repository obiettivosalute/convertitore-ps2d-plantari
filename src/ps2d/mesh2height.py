"""Conversione di una mesh (STL, OBJ, PLY...) nella mappa quote del PS2D.

Il formato PS2D descrive la geometria come mappa 2.5D: una sola quota per
ogni cella di una griglia regolare da 0,5 mm. Un plantare in STL e' invece
un solido chiuso, quindi va proiettato: si tiene la faccia utile (per
impostazione predefinita quella superiore, dove appoggia il piede) e si
scarta il resto.

La proiezione avviene infittendo la mesh finche' ogni lato e' piu' corto di
mezzo pixel, poi riportando i vertici sulla griglia con un z-buffer. Cosi'
non servono intersezioni raggio-triangolo e il risultato resta preciso
anche sui bordi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

try:
    import trimesh
except ImportError:  # pragma: no cover
    trimesh = None

from scipy import ndimage

ESTENSIONI_SUPPORTATE = {".stl", ".obj", ".ply", ".off", ".3mf", ".glb", ".gltf"}


@dataclass
class RisultatoConversione:
    """Esito della proiezione di una mesh sulla griglia."""

    quote_mm: np.ndarray          # float32, quota in mm sopra il piano minimo
    maschera: np.ndarray          # bool, celle che contengono geometria
    mm_per_px: float
    lunghezza_mm: float
    larghezza_mm: float
    altezza_mm: float
    n_vertici: int
    n_facce: int
    asse_verticale: str
    celle_riempite: int = 0
    avvisi: list[str] = field(default_factory=list)

    @property
    def area_cm2(self) -> float:
        return float(self.maschera.sum()) * self.mm_per_px ** 2 / 100.0


def carica_mesh(path: str | Path):
    """Carica una mesh da file e la restituisce come oggetto trimesh."""
    if trimesh is None:
        raise RuntimeError("la libreria trimesh non e' installata")
    path = Path(path)
    if path.suffix.lower() not in ESTENSIONI_SUPPORTATE:
        raise ValueError(f"estensione non supportata: {path.suffix}")
    mesh = trimesh.load(str(path), force="mesh", process=False)
    if not hasattr(mesh, "vertices") or len(mesh.vertices) == 0:
        raise ValueError("il file non contiene una mesh valida")
    return mesh


def rileva_unita(dim: np.ndarray) -> tuple[float, str]:
    """Deduce l'unita' di misura del file dalle dimensioni del modello.

    Nessun formato di mesh dichiara l'unita': STL e OBJ contengono numeri
    puri. Un plantare misura circa 250 mm, quindi il valore della dimensione
    maggiore dice da solo in che scala e' il file. Gli OBJ prodotti dallo
    scanner, per esempio, sono in metri.
    """
    massimo = float(np.max(dim))
    if massimo <= 0:
        return 1.0, "mm"
    if massimo < 1.5:
        return 1000.0, "m"
    if massimo < 45.0:
        return 10.0, "cm"
    return 1.0, "mm"


def _rileva_assi(dim: np.ndarray) -> tuple[int, int, int]:
    """Deduce quale asse e' verticale, quale longitudinale, quale trasversale.

    Un plantare e' molto piu' lungo che largo e molto piu' largo che alto:
    l'asse con estensione minima e' il verticale, quello massimo la lunghezza.
    """
    ordine = np.argsort(dim)          # crescente
    return int(ordine[0]), int(ordine[2]), int(ordine[1])


def converti(
    mesh,
    mm_per_px: float = 0.5,
    frame: tuple[int, int] | None = None,
    margine_mm: float = 8.0,
    superficie: str = "superiore",
    asse_verticale: int | None = None,
    ruota_gradi: float = 0.0,
    unita: str = "auto",
    centra: bool = True,
    tolleranza_faccia_mm: float | None = None,
    specchia: bool = False,
) -> RisultatoConversione:
    """Proietta la mesh sulla griglia e restituisce le quote in millimetri.

    superficie: "superiore" tiene la faccia rivolta verso l'alto,
    "inferiore" quella verso il basso. Su un piede scansionato intero la
    pianta e' quasi sempre la faccia inferiore; su un plantare gia'
    modellato e' la superiore, dove appoggia il piede.
    specchia: ribalta l'asse trasversale, per quando lo scanner produce il
    piede rovesciato rispetto al lato dichiarato.
    unita: "auto" deduce la scala dalle dimensioni, oppure "mm", "cm", "m".
    tolleranza_faccia_mm: spessore della fascia, sotto il punto piu' alto di
    ogni cella, entro cui i campioni sono considerati parte della faccia
    superiore. Se omesso vale un pixel.
    """
    avvisi: list[str] = []
    V = np.asarray(mesh.vertices, dtype=np.float64)
    F = np.asarray(mesh.faces, dtype=np.int64)

    dim = V.max(axis=0) - V.min(axis=0)
    if unita == "auto":
        fattore, rilevata = rileva_unita(dim)
        if fattore != 1.0:
            avvisi.append(f"unita' rilevata: {rilevata} (valori moltiplicati "
                          f"per {fattore:g} per ottenere millimetri)")
    else:
        fattore = {"mm": 1.0, "cm": 10.0, "m": 1000.0}[unita]
    if fattore != 1.0:
        V = V * fattore
        dim = dim * fattore
    if asse_verticale is None:
        iv, il, it = _rileva_assi(dim)
    else:
        iv = int(asse_verticale)
        restanti = [a for a in (0, 1, 2) if a != iv]
        il = restanti[int(np.argmax(dim[restanti]))]
        it = restanti[int(np.argmin(dim[restanti]))]

    nomi = "XYZ"
    # riordina in (trasversale, longitudinale, verticale) = (x, y, z) di lavoro
    P = V[:, [it, il, iv]].copy()

    if superficie == "inferiore":
        P[:, 2] = -P[:, 2]

    if specchia:
        P[:, 0] = -P[:, 0]

    if ruota_gradi:
        a = np.deg2rad(ruota_gradi)
        c, s = np.cos(a), np.sin(a)
        centro = P[:, :2].mean(axis=0)
        xy = P[:, :2] - centro
        P[:, 0] = xy[:, 0] * c - xy[:, 1] * s + centro[0]
        P[:, 1] = xy[:, 0] * s + xy[:, 1] * c + centro[1]

    lung = float(P[:, 1].max() - P[:, 1].min())
    larg = float(P[:, 0].max() - P[:, 0].min())
    alt = float(P[:, 2].max() - P[:, 2].min())

    # --- infittimento: ogni lato piu' corto di mezzo pixel ---
    lato_max = mm_per_px * 0.5
    Vd, Fd = P, F
    if trimesh is not None and len(F):
        try:
            # area calcolata sui vertici gia' riscalati in millimetri
            t = P[F]
            area = float(np.linalg.norm(
                np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1).sum() / 2.0)
            stima = int((area / (lato_max ** 2)) * 1.2) if area else 0
            if stima > 4_000_000:
                lato_max = mm_per_px          # meno fitto, ma sostenibile
                avvisi.append(
                    "mesh molto densa: infittimento ridotto per non esaurire la memoria"
                )
            Vd, Fd = trimesh.remesh.subdivide_to_size(P, F, max_edge=lato_max)
        except Exception as exc:              # pragma: no cover
            avvisi.append(f"infittimento non riuscito ({exc}): uso i vertici originali")
            Vd = P

    # --- griglia ---
    if frame is None:
        w = int(np.ceil((larg + 2 * margine_mm) / mm_per_px))
        h = int(np.ceil((lung + 2 * margine_mm) / mm_per_px))
    else:
        w, h = frame

    if centra:
        cx = (P[:, 0].max() + P[:, 0].min()) / 2.0
        cy = (P[:, 1].max() + P[:, 1].min()) / 2.0
        x0 = cx - w * mm_per_px / 2.0
        y0 = cy - h * mm_per_px / 2.0
    else:
        # coordinate assolute: la cella (0,0) corrisponde all'origine del modello
        x0 = y0 = 0.0

    ix = np.floor((Vd[:, 0] - x0) / mm_per_px).astype(np.int64)
    iy = np.floor((Vd[:, 1] - y0) / mm_per_px).astype(np.int64)
    dentro = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
    if not dentro.all():
        persi = int((~dentro).sum())
        avvisi.append(
            f"{persi} punti fuori dal fotogramma {w}x{h} px: il modello e' piu' "
            "grande della griglia e verra' tagliato"
        )
    ix, iy, z = ix[dentro], iy[dentro], Vd[dentro, 2]

    # --- proiezione in due passaggi ---
    # Il primo trova la faccia superiore (quota massima per cella), il secondo
    # media i soli campioni che le appartengono. Fermarsi al massimo darebbe
    # una sovrastima sistematica: su una superficie inclinata il punto piu'
    # alto caduto nella cella sta sul suo bordo, non al centro. Mediando i
    # campioni della sola faccia superiore si ottiene invece il valore
    # centrale, che e' quello che la mappa quote deve contenere.
    if tolleranza_faccia_mm is None:
        tolleranza_faccia_mm = mm_per_px

    cella = iy * w + ix
    ordine = np.lexsort((z, cella))
    cella_ord, z_ord = cella[ordine], z[ordine]
    ultimo = np.append(np.nonzero(np.diff(cella_ord))[0], len(cella_ord) - 1)

    zmax = np.full(h * w, -np.inf)
    zmax[cella_ord[ultimo]] = z_ord[ultimo]

    faccia = z > zmax[cella] - tolleranza_faccia_mm
    somma = np.bincount(cella[faccia], weights=z[faccia], minlength=h * w)
    conta = np.bincount(cella[faccia], minlength=h * w)
    with np.errstate(invalid="ignore", divide="ignore"):
        media = somma / np.where(conta == 0, np.nan, conta)

    quote = np.where(conta > 0, media, -np.inf).reshape(h, w)
    maschera = np.isfinite(quote)

    if not maschera.any():
        raise ValueError("la proiezione non ha prodotto alcun punto valido")

    # --- chiusura dei buchi interni ---
    pieno = ndimage.binary_fill_holes(maschera)
    buchi = pieno & ~maschera
    n_buchi = int(buchi.sum())
    if n_buchi:
        q = quote.copy()
        q[~maschera] = np.nan
        # media dei vicini validi, ripetuta finche' i buchi si chiudono
        for _ in range(12):
            if not np.isnan(q[pieno]).any():
                break
            valido = ~np.isnan(q)
            somma = ndimage.uniform_filter(np.nan_to_num(q), size=3) * 9
            conta = ndimage.uniform_filter(valido.astype(float), size=3) * 9
            with np.errstate(invalid="ignore", divide="ignore"):
                media = somma / np.where(conta == 0, np.nan, conta)
            da_riempire = pieno & np.isnan(q) & ~np.isnan(media)
            q[da_riempire] = media[da_riempire]
        quote = np.where(np.isnan(q), -np.inf, q)
        maschera = np.isfinite(quote)
        avvisi.append(f"chiusi {n_buchi} pixel vuoti interni al contorno")

    base = quote[maschera].min()
    quote_mm = np.where(maschera, quote - base, 0.0).astype(np.float32)

    return RisultatoConversione(
        quote_mm=quote_mm,
        maschera=maschera,
        mm_per_px=mm_per_px,
        lunghezza_mm=lung,
        larghezza_mm=larg,
        altezza_mm=alt,
        n_vertici=len(V),
        n_facce=len(F),
        asse_verticale=nomi[iv],
        celle_riempite=n_buchi,
        avvisi=avvisi,
    )


def quantizza(risultato: RisultatoConversione) -> tuple[np.ndarray, float]:
    """Converte le quote in millimetri nel formato uint16 del .sca.

    Nel formato lo zero e' il punto piu' vicino al sensore, cioe' il piu'
    alto: il valore cresce scendendo. Lo sfondo vale 65535.
    """
    from config import SFONDO_SCA

    q = risultato.quote_mm
    m = risultato.maschera
    escursione = float(q[m].max() - q[m].min())
    if escursione <= 0:
        escursione = 1e-3
    mm_per_unita = escursione / (SFONDO_SCA - 1)

    alto = float(q[m].max())
    valori = np.full(q.shape, SFONDO_SCA, dtype=np.uint16)
    dist = (alto - q[m]) / mm_per_unita
    valori[m] = np.clip(np.rint(dist), 0, SFONDO_SCA - 1).astype(np.uint16)
    return valori, mm_per_unita


def valuta_verso(risultato: RisultatoConversione) -> tuple[str, str]:
    """Dice se la superficie plantare sembra orientata nel verso giusto.

    In una pianta di piede le zone di appoggio — tallone, avampiede, bordo
    laterale — occupano gran parte dell'area e stanno tutte vicine al
    sensore; l'arco e' una minoranza che se ne allontana. La distribuzione
    delle quote e' quindi nettamente asimmetrica, con la massa verso l'alto
    e una coda verso il basso.

    Sulla scansione autentica usata come riferimento: 81% dell'area nella
    meta' alta e asimmetria -1,31. Rovesciando l'asse i due valori
    diventano 19% e +1,31, quindi il criterio separa i due casi con ampio
    margine.

    Restituisce (esito, spiegazione) con esito in {"corretto", "rovesciato",
    "incerto"}.
    """
    q = risultato.quote_mm[risultato.maschera]
    if q.size < 100:
        return "incerto", "troppi pochi punti per giudicare"

    lo, hi = float(q.min()), float(q.max())
    if hi <= lo:
        return "incerto", "superficie piatta"
    area_alta = float((q > (lo + hi) / 2).mean())
    scarto = float(q.std())
    asimmetria = float(((q - q.mean()) ** 3).mean() / scarto ** 3) if scarto else 0.0

    dettaglio = (f"area nella metà alta {area_alta*100:.0f}%, "
                 f"asimmetria {asimmetria:+.2f}")

    if area_alta >= 0.60 and asimmetria <= -0.30:
        return "corretto", dettaglio
    if area_alta <= 0.40 and asimmetria >= 0.30:
        return "rovesciato", dettaglio
    return "incerto", dettaglio


def controlla_plausibilita(risultato: RisultatoConversione) -> list[str]:
    """Verifiche di buon senso sulle dimensioni, per intercettare unita' errate."""
    from config import (ALTEZZA_MASSIMA_ATTESA_MM, ALTEZZA_MINIMA_ATTESA_MM,
                        LUNGHEZZA_MAX_MM, LUNGHEZZA_MIN_MM)

    messaggi: list[str] = []
    L = risultato.lunghezza_mm
    if L < LUNGHEZZA_MIN_MM or L > LUNGHEZZA_MAX_MM:
        messaggi.append(
            f"lunghezza {L:.0f} mm fuori dall'intervallo atteso "
            f"({LUNGHEZZA_MIN_MM:.0f}-{LUNGHEZZA_MAX_MM:.0f} mm): "
            "il file potrebbe essere in centimetri o in pollici"
        )
    A = risultato.altezza_mm
    if A < ALTEZZA_MINIMA_ATTESA_MM:
        messaggi.append(f"altezza {A:.1f} mm molto bassa: il modello sembra piatto")
    elif A > ALTEZZA_MASSIMA_ATTESA_MM:
        messaggi.append(f"altezza {A:.1f} mm elevata: verificare l'orientamento")
    return messaggi
