"""Anteprima della mappa quote: colori per altezza e isoipse ogni 5 mm.

Serve a controllare a colpo d'occhio che il modello sia orientato bene e
che la superficie proiettata sia quella giusta, prima di mandarlo in fresa.
"""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget


def _scala_colori(v: np.ndarray) -> np.ndarray:
    """Rampa dal blu al rosso passando per verde e giallo."""
    v = np.clip(v, 0, 1)
    r = np.clip(1.5 - np.abs(4 * v - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * v - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * v - 1), 0, 1)
    return np.stack([r, g, b], axis=-1)


def rendi_mappa(quote_mm: np.ndarray, maschera: np.ndarray,
                passo_isoipse_mm: float = 5.0) -> QImage:
    """Costruisce l'immagine a colori della mappa quote."""
    h, w = quote_mm.shape
    img = np.full((h, w, 3), 250, dtype=np.uint8)

    if maschera.any():
        q = quote_mm.copy()
        lo, hi = q[maschera].min(), q[maschera].max()
        norm = (q - lo) / (hi - lo) if hi > lo else np.zeros_like(q)
        colori = (_scala_colori(norm) * 255).astype(np.uint8)

        # rilievo: un po' di ombreggiatura per leggere le forme
        gy, gx = np.gradient(np.where(maschera, q, lo).astype(np.float64))
        ombra = np.clip(0.5 + 0.35 * (-gx - gy), 0.25, 1.35)
        colori = np.clip(colori * ombra[..., None], 0, 255).astype(np.uint8)
        img[maschera] = colori[maschera]

        if passo_isoipse_mm > 0 and hi > lo:
            livello = np.floor(q / passo_isoipse_mm).astype(np.int32)
            bordo = np.zeros((h, w), dtype=bool)
            bordo[:-1] |= (livello[:-1] != livello[1:]) & maschera[:-1] & maschera[1:]
            bordo[:, :-1] |= ((livello[:, :-1] != livello[:, 1:])
                              & maschera[:, :-1] & maschera[:, 1:])
            img[bordo] = (img[bordo] * 0.45).astype(np.uint8)

    # l'asse verticale della griglia cresce verso il basso: si capovolge
    img = np.ascontiguousarray(img[::-1])
    return QImage(img.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()


class WidgetAnteprima(QWidget):
    """Riquadro con l'anteprima di un piede e le sue misure."""

    def __init__(self, titolo: str, parent=None):
        super().__init__(parent)
        self.titolo = titolo
        disposizione = QVBoxLayout(self)
        disposizione.setContentsMargins(4, 4, 4, 4)
        disposizione.setSpacing(4)

        self.etichetta_titolo = QLabel(titolo)
        self.etichetta_titolo.setStyleSheet("font-weight: bold;")
        self.immagine = QLabel("nessun file")
        self.immagine.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.immagine.setMinimumSize(220, 380)
        self.immagine.setStyleSheet(
            "background:#f4f4f4; border:1px solid #ccc; color:#888;")
        self.immagine.setSizePolicy(QSizePolicy.Policy.Expanding,
                                    QSizePolicy.Policy.Expanding)
        self.verso = QLabel("")
        self.verso.setWordWrap(True)
        self.verso.setStyleSheet("font-size: 11px;")
        self.misure = QLabel("—")
        self.misure.setWordWrap(True)
        self.misure.setStyleSheet("color:#444; font-size: 11px;")

        disposizione.addWidget(self.etichetta_titolo)
        disposizione.addWidget(self.immagine, 1)
        disposizione.addWidget(self.verso)
        disposizione.addWidget(self.misure)
        self._pixmap: QPixmap | None = None

    def mostra(self, risultato) -> None:
        """Aggiorna anteprima, giudizio sull'orientamento e misure."""
        from src.ps2d import valuta_verso

        immagine = rendi_mappa(risultato.quote_mm, risultato.maschera)
        self._pixmap = QPixmap.fromImage(immagine)
        self._ridisegna()

        esito, dettaglio = valuta_verso(risultato)
        if esito == "corretto":
            self.verso.setText(
                f"✔ appoggio in rosso, arco in blu: verso corretto ({dettaglio})")
            self.verso.setStyleSheet("color:#161; font-size:11px;")
        elif esito == "rovesciato":
            self.verso.setText(
                f"✘ superficie rovesciata ({dettaglio}) — cambia «Superficie "
                "da usare»: l'appoggio deve risultare rosso, l'arco blu")
            self.verso.setStyleSheet("color:#b00; font-size:11px; font-weight:bold;")
        else:
            self.verso.setText(
                f"? verso non riconoscibile ({dettaglio}) — controlla a occhio: "
                "tallone e avampiede devono essere rossi, l'arco blu")
            self.verso.setStyleSheet("color:#a60; font-size:11px;")

        ys, xs = np.nonzero(risultato.maschera)
        L = (ys.max() - ys.min() + 1) * risultato.mm_per_px
        W = (xs.max() - xs.min() + 1) * risultato.mm_per_px
        q = risultato.quote_mm[risultato.maschera]
        self.misure.setText(
            f"ingombro proiettato {L:.0f} x {W:.0f} mm · "
            f"rilievo {q.max() - q.min():.1f} mm · "
            f"area {risultato.area_cm2:.0f} cm² · "
            f"mesh {risultato.n_vertici:,} vertici, {risultato.n_facce:,} facce · "
            f"asse verticale {risultato.asse_verticale}")

    def pulisci(self, messaggio: str = "nessun file") -> None:
        self._pixmap = None
        self.immagine.setPixmap(QPixmap())
        self.immagine.setText(messaggio)
        self.verso.setText("")
        self.misure.setText("—")

    def _ridisegna(self) -> None:
        if self._pixmap is None:
            return
        self.immagine.setPixmap(self._pixmap.scaled(
            self.immagine.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, evento):  # noqa: N802 (nome imposto da Qt)
        super().resizeEvent(evento)
        self._ridisegna()
