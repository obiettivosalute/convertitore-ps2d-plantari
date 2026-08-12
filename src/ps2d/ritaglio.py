"""Isolamento dell'impronta dal piano che la circonda.

Scansionando un calco in schiuma non si acquisisce solo l'impronta: entra
tutto il blocco, con la sua superficie piana attorno. Lo stesso capita
scansionando un piede appoggiato, quando lo scanner riprende anche il piano
d'appoggio. Quella superficie in piu' non e' geometria utile e va tolta,
altrimenti finisce nella mappa quote e falsa misure e ingombri.

Il piano si riconosce da solo: e' una grande area a quota pressoche'
costante, e nella mappa quote sta in basso, perche' e' la parte piu'
lontana dal sensore. L'impronta e' quello che sporge sopra di esso.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage


@dataclass
class EsitoRitaglio:
    """Cosa e' stato tolto, e perche'."""

    maschera: np.ndarray
    applicato: bool
    quota_piano_mm: float = 0.0
    soglia_mm: float = 0.0
    celle_prima: int = 0
    celle_dopo: int = 0
    motivo: str = ""

    @property
    def scartato_pct(self) -> float:
        if not self.celle_prima:
            return 0.0
        return 100.0 * (self.celle_prima - self.celle_dopo) / self.celle_prima


def trova_piano(quote_mm: np.ndarray, maschera: np.ndarray,
                bin_mm: float = 0.5) -> tuple[float, float]:
    """Cerca la quota del piano e quanta area occupa.

    Restituisce (quota_del_piano, frazione_di_area). Se non c'e' un piano
    evidente la frazione risulta bassa e chi chiama lascia perdere.
    """
    q = quote_mm[maschera]
    if q.size < 500:
        return 0.0, 0.0
    lo, hi = float(q.min()), float(q.max())
    if hi - lo < 3.0:
        return 0.0, 0.0

    n = max(8, int((hi - lo) / bin_mm))
    conteggi, bordi = np.histogram(q, bins=n, range=(lo, hi))

    # il piano sta nella parte bassa: e' la zona piu' lontana dal sensore
    limite = int(n * 0.55)
    if limite < 2:
        return 0.0, 0.0
    i = int(np.argmax(conteggi[:limite]))
    quota = float((bordi[i] + bordi[i + 1]) / 2)

    # quanta area sta entro un paio di millimetri da quella quota
    vicino = float(np.mean(np.abs(q - quota) <= 2.0))
    return quota, vicino


def isola_impronta(quote_mm: np.ndarray, maschera: np.ndarray,
                   margine_mm: float = 4.0,
                   area_minima_piano: float = 0.12,
                   area_minima_impronta_cm2: float = 100.0,
                   scarto_massimo: float = 0.70,
                   mm_per_px: float = 0.5) -> EsitoRitaglio:
    """Toglie il piano e tiene la sola impronta.

    margine_mm: quanto sopra il piano deve stare un punto per essere
    considerato impronta. Serve a non far entrare le irregolarita' della
    superficie piana.

    Le due soglie di sicurezza servono contro i falsi allarmi. Un plantare
    gia' modellato ha spesso una zona piatta estesa che somiglia a un piano
    di appoggio, ma e' superficie utile: se quello che resterebbe e' troppo
    piccolo per essere un'impronta, o se si butterebbe via la maggior parte
    di cio' che e' stato acquisito, e' piu' prudente non toccare nulla e
    dirlo.
    """
    esito = EsitoRitaglio(maschera=maschera, applicato=False,
                          celle_prima=int(maschera.sum()),
                          celle_dopo=int(maschera.sum()))

    quota, frazione = trova_piano(quote_mm, maschera)
    esito.quota_piano_mm = quota
    if frazione < area_minima_piano:
        esito.motivo = (f"nessun piano evidente da togliere "
                        f"(area piatta {frazione*100:.0f}%)")
        return esito

    soglia = quota + margine_mm
    esito.soglia_mm = soglia
    sopra = maschera & (quote_mm > soglia)
    if not sopra.any():
        esito.motivo = "sopra il piano non resta nulla: ritaglio non applicato"
        return esito

    # la componente connessa piu' estesa e' l'impronta; il resto e' rumore
    etichette, quante = ndimage.label(sopra)
    if quante == 0:
        esito.motivo = "nessuna zona sopra il piano"
        return esito
    dimensioni = ndimage.sum(sopra, etichette, range(1, quante + 1))
    principale = int(np.argmax(dimensioni)) + 1
    impronta = etichette == principale
    impronta = ndimage.binary_fill_holes(impronta)

    area_cm2 = impronta.sum() * mm_per_px ** 2 / 100.0
    if area_cm2 < area_minima_impronta_cm2:
        esito.motivo = (f"la zona trovata e' troppo piccola per essere "
                        f"un'impronta ({area_cm2:.0f} cm²): ritaglio non applicato")
        return esito

    scarto = 1.0 - impronta.sum() / max(1, maschera.sum())
    if scarto > scarto_massimo:
        esito.motivo = (f"il ritaglio butterebbe via il {scarto*100:.0f}% di "
                        f"quanto acquisito: troppo, ritaglio non applicato. "
                        f"Se il modello e' un plantare e non una scansione, "
                        f"togli la spunta")
        return esito

    esito.maschera = impronta
    esito.applicato = True
    esito.celle_dopo = int(impronta.sum())
    esito.motivo = (f"tolto il piano a quota {quota:.1f} mm "
                    f"(soglia {soglia:.1f} mm): "
                    f"scartato il {esito.scartato_pct:.0f}% dell'area acquisita")
    return esito


def applica(quote_mm: np.ndarray, esito: EsitoRitaglio) -> np.ndarray:
    """Riporta a zero le quote fuori dall'impronta, come vuole il formato."""
    return np.where(esito.maschera, quote_mm, 0.0).astype(np.float32)
