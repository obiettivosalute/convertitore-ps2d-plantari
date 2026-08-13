"""Finestra di ispezione di un pacchetto PS2D.

Il lettore raccoglie molto piu' di quanto stia in un riepilogo di cinque
righe: l'inventario dei file dentro i due archivi annidati, i campi del
.his di ciascun piede, il manifest dell'invio, gli header dei layer e la
mappa quote. Qui viene mostrato tutto, una scheda per aspetto, e si puo'
salvare su file per confrontare a freddo due pacchetti.
"""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout,
                             QHeaderView, QLabel, QMessageBox, QPushButton,
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QTextEdit, QVBoxLayout, QWidget)

from src.ps2d import ContenutoPS2D, osservazioni, report, report_dati

from .anteprima import rendi_mappa

MONOSPAZIO = "font-family: Consolas, monospace;"


def _tabella(intestazioni: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(intestazioni))
    t.setHorizontalHeaderLabels(intestazioni)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    return t


def _riga(tabella: QTableWidget, valori: list[str],
          allinea_a_destra: set[int] = frozenset()) -> None:
    r = tabella.rowCount()
    tabella.insertRow(r)
    for c, v in enumerate(valori):
        voce = QTableWidgetItem(v)
        if c in allinea_a_destra:
            voce.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                  | Qt.AlignmentFlag.AlignVCenter)
        tabella.setItem(r, c, voce)


def _byte(n: int) -> str:
    return f"{n:,}".replace(",", ".")


class _Mappa(QLabel):
    """Mappa quote di un piede, ridimensionata insieme alla finestra."""

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 320)
        self.setStyleSheet("background:#f4f4f4; border:1px solid #ccc;")
        self._ridisegna()

    def _ridisegna(self) -> None:
        self.setPixmap(self._pixmap.scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, evento):  # noqa: N802 (nome imposto da Qt)
        super().resizeEvent(evento)
        self._ridisegna()


class FinestraIspezione(QWidget):
    """Vista completa del contenuto di un pacchetto."""

    def __init__(self, contenuto: ContenutoPS2D, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.contenuto = contenuto
        self.setWindowTitle(f"Ispezione — {contenuto.percorso.name}")
        self.resize(1040, 760)

        schede = QTabWidget()
        schede.addTab(self._scheda_riepilogo(), "Riepilogo")
        schede.addTab(self._scheda_file(),
                      f"File ({len(contenuto.elenco_file)})")
        schede.addTab(self._scheda_anagrafica(), "Anagrafica")
        schede.addTab(self._scheda_manifest(), "Manifest")
        schede.addTab(self._scheda_geometria(), "Geometria")
        schede.addTab(self._scheda_anteprime(), "Anteprime")

        esporta_txt = QPushButton("Esporta report…")
        esporta_txt.clicked.connect(self._esporta)
        chiudi = QPushButton("Chiudi")
        chiudi.clicked.connect(self.close)

        barra = QHBoxLayout()
        barra.addWidget(QLabel(f"{_byte(contenuto.dimensione)} byte"))
        barra.addStretch(1)
        barra.addWidget(esporta_txt)
        barra.addWidget(chiudi)

        disposizione = QVBoxLayout(self)
        disposizione.addWidget(schede, 1)
        disposizione.addLayout(barra)

    # ---------------------------------------------------------------- schede

    def _scheda_riepilogo(self) -> QWidget:
        c = self.contenuto
        r = [f"Pacchetto   {c.percorso.name}",
             f"Cartella    {c.percorso.parent}",
             f"Dimensione  {_byte(c.dimensione)} byte"]
        if c.ps2d_interno:
            r.append(f"PS2D interno  {c.ps2d_interno}")
        if c.anagrafica:
            a = c.anagrafica
            r.append(f"Paziente    {a.get('name','?')} {a.get('vname','?')}"
                     f"  ({a.get('gebdat','?')})")
        if c.manifest:
            r.append("Clinica     "
                     f"{c.manifest.get('clinic', {}).get('name', '?')}")
        r.append("")
        for lato, v in sorted(c.lati.items()):
            lung, larg = v.ingombro_mm()
            r.append(f"{lato:<8s}{v.larghezza}x{v.altezza} px @ {v.mm_per_px} mm"
                     f"   ingombro {lung:.0f}x{larg:.0f} mm"
                     f"   escursione {v.escursione_mm:.1f} mm"
                     f"   area {v.area_cm2:.0f} cm²")

        note = osservazioni(c)
        if note:
            r.append("")
            r.append("Osservazioni")
            for n in note:
                r.append(f"  • {n}")

        area = QTextEdit()
        area.setReadOnly(True)
        area.setStyleSheet(MONOSPAZIO)
        area.setPlainText("\n".join(r))
        return area

    def _scheda_file(self) -> QWidget:
        t = _tabella(["Nome", "Contenitore", "Lato", "Byte", "Compressi",
                      "Tipo"])
        for f in self.contenuto.elenco_file:
            _riga(t, [f.nome, f.contenitore, f.lato, _byte(f.dimensione),
                      _byte(f.compressa), f.tipo], allinea_a_destra={3, 4})
        t.setSortingEnabled(True)
        t.resizeColumnsToContents()
        t.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive)
        return t

    def _scheda_anagrafica(self) -> QWidget:
        c = self.contenuto
        lati = sorted(c.lati)
        if not c.anagrafica:
            return self._testo("Nessun file .his trovato nel pacchetto.")

        # una colonna per piede: se i due .his divergono si vede subito
        t = _tabella(["Campo", "Pacchetto"] + lati)
        campi = list(c.anagrafica)
        for lato in lati:
            for k in c.lati[lato].anagrafica:
                if k not in campi:
                    campi.append(k)
        for k in campi:
            valori = [k, str(c.anagrafica.get(k, ""))]
            valori += [str(c.lati[l].anagrafica.get(k, "")) for l in lati]
            _riga(t, valori)
        t.resizeColumnsToContents()
        return t

    def _scheda_manifest(self) -> QWidget:
        if not self.contenuto.manifest:
            return self._testo(
                "Nessun manifest: il file aperto e' un .ps2d nudo, non "
                "l'archivio di invio che lo contiene.")
        return self._testo(json.dumps(self.contenuto.manifest, indent=2,
                                      ensure_ascii=False))

    def _scheda_geometria(self) -> QWidget:
        lati = sorted(self.contenuto.lati)
        if not lati:
            return self._testo("Nessun layer .sca trovato.")

        voci: list[tuple[str, callable]] = [
            ("firma dell'header", lambda v: v.firma),
            ("griglia (px)", lambda v: f"{v.larghezza} x {v.altezza}"),
            ("passo (mm/px)", lambda v: f"{v.mm_per_px} x {v.mm_per_px_y}"),
            ("mm per unità di quota", lambda v: f"{v.mm_per_unita_z:.8f}"),
            ("fondo scala (mm)", lambda v: f"{v.fondo_scala_mm:.1f}"),
            ("pixel validi", lambda v: _byte(v.pixel_validi)),
            ("copertura del fotogramma", lambda v: f"{v.copertura_pct:.1f} %"),
            ("area utile (cm²)", lambda v: f"{v.area_cm2:.1f}"),
            ("ingombro (mm)",
             lambda v: "{:.0f} x {:.0f}".format(*v.ingombro_mm())),
            ("escursione (mm)", lambda v: f"{v.escursione_mm:.1f}"),
            ("layer presenti", lambda v: ", ".join(sorted(v.file))),
        ]
        t = _tabella(["Grandezza"] + lati)
        for etichetta, estrai in voci:
            _riga(t, [etichetta] + [estrai(self.contenuto.lati[l])
                                    for l in lati])
        t.resizeColumnsToContents()
        return t

    def _scheda_anteprime(self) -> QWidget:
        contenitore = QWidget()
        riga = QHBoxLayout(contenitore)
        mostrate = 0
        for lato, v in sorted(self.contenuto.lati.items()):
            if v.quote_mm is None or v.maschera is None:
                continue
            colonna = QVBoxLayout()
            titolo = QLabel(f"{lato}  —  escursione {v.escursione_mm:.1f} mm")
            titolo.setStyleSheet("font-weight: bold;")
            colonna.addWidget(titolo)
            colonna.addWidget(
                _Mappa(QPixmap.fromImage(rendi_mappa(v.quote_mm, v.maschera))), 1)
            riga.addLayout(colonna, 1)
            mostrate += 1
        if not mostrate:
            return self._testo("Geometria non caricata: nessuna mappa da "
                               "disegnare.")
        return contenitore

    # ---------------------------------------------------------------- utilita'

    def _testo(self, contenuto: str) -> QTextEdit:
        area = QTextEdit()
        area.setReadOnly(True)
        area.setStyleSheet(MONOSPAZIO)
        area.setPlainText(contenuto)
        return area

    def _esporta(self) -> None:
        base = self.contenuto.percorso
        proposto = str(base.with_name(base.stem + "_report.txt"))
        percorso, filtro = QFileDialog.getSaveFileName(
            self, "Salva il report", proposto,
            "Report di testo (*.txt);;Dati JSON (*.json)")
        if not percorso:
            return

        destinazione = Path(percorso)
        vuole_json = (destinazione.suffix.lower() == ".json"
                      or "json" in filtro.lower())
        try:
            if vuole_json:
                if destinazione.suffix.lower() != ".json":
                    destinazione = destinazione.with_suffix(".json")
                testo = json.dumps(report_dati(self.contenuto), indent=2,
                                   ensure_ascii=False)
            else:
                testo = report(self.contenuto)
            # UTF-8 esplicito: il report contiene simboli che la codifica
            # predefinita di Windows non regge.
            destinazione.write_text(testo, encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return

        QMessageBox.information(self, "Report salvato", str(destinazione))
