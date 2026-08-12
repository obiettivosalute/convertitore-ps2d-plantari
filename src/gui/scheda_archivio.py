"""Storico delle lavorazioni, con riapertura della cartella e riesportazione."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView,
                             QLabel, QLineEdit, QMessageBox, QPushButton,
                             QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)

from src.db import Archivio
from src.servizio import riesporta


def apri_nel_gestore_file(percorso: Path) -> None:
    """Apre la cartella nel gestore di file del sistema."""
    percorso = Path(percorso)
    if not percorso.exists():
        raise FileNotFoundError(percorso)
    if sys.platform == "win32":
        os.startfile(percorso)                                  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.run(["open", str(percorso)], check=False)
    else:
        subprocess.run(["xdg-open", str(percorso)], check=False)


class SchedaArchivio(QWidget):
    """Tabella delle lavorazioni salvate."""

    COLONNE = ["Data", "Cliente", "Nascita", "Descrizione", "Stato",
               "Pacchetto", "Cartella"]

    def __init__(self, archivio: Archivio, parent=None):
        super().__init__(parent)
        self.archivio = archivio
        disposizione = QVBoxLayout(self)

        barra = QHBoxLayout()
        self.filtro = QLineEdit()
        self.filtro.setPlaceholderText("filtra per cognome, nome o descrizione")
        self.filtro.textChanged.connect(self.ricarica)
        bottone_aggiorna = QPushButton("Aggiorna")
        bottone_aggiorna.clicked.connect(self.ricarica)
        self.bottone_apri = QPushButton("Apri cartella")
        self.bottone_apri.clicked.connect(self._apri)
        self.bottone_riesporta = QPushButton("Rigenera pacchetto")
        self.bottone_riesporta.clicked.connect(self._riesporta)
        self.bottone_elimina = QPushButton("Elimina")
        self.bottone_elimina.clicked.connect(self._elimina)
        barra.addWidget(self.filtro, 1)
        barra.addWidget(bottone_aggiorna)
        barra.addWidget(self.bottone_apri)
        barra.addWidget(self.bottone_riesporta)
        barra.addWidget(self.bottone_elimina)
        disposizione.addLayout(barra)

        self.tabella = QTableWidget(0, len(self.COLONNE))
        self.tabella.setHorizontalHeaderLabels(self.COLONNE)
        self.tabella.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabella.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.tabella.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabella.verticalHeader().setVisible(False)
        self.tabella.doubleClicked.connect(self._apri)
        intestazione = self.tabella.horizontalHeader()
        intestazione.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        disposizione.addWidget(self.tabella, 1)

        self.riepilogo = QLabel("")
        self.riepilogo.setStyleSheet("color:#555;")
        disposizione.addWidget(self.riepilogo)

        self.ricarica()

    def ricarica(self) -> None:
        righe = self.archivio.elenca_lavorazioni(filtro=self.filtro.text())
        self.tabella.setRowCount(len(righe))
        for i, r in enumerate(righe):
            data = r["creata_il"].replace("T", "  ")
            valori = [
                data,
                f"{r['cognome']} {r['nome']}",
                r["data_nascita"],
                r["descrizione"] or "",
                r["stato"],
                Path(r["ps2d"]).name if r["ps2d"] else "—",
                r["cartella"] or "—",
            ]
            for j, v in enumerate(valori):
                voce = QTableWidgetItem(str(v))
                if j == 0:
                    voce.setData(Qt.ItemDataRole.UserRole, r["id"])
                self.tabella.setItem(i, j, voce)
        self.tabella.resizeColumnsToContents()
        s = self.archivio.riepilogo()
        self.riepilogo.setText(
            f"{s['clienti']} clienti · {s['lavorazioni']} lavorazioni · "
            f"{s['esportate']} pacchetti generati")

    def _selezionata(self) -> tuple[int, dict] | None:
        riga = self.tabella.currentRow()
        if riga < 0:
            return None
        voce = self.tabella.item(riga, 0)
        identificativo = voce.data(Qt.ItemDataRole.UserRole)
        dati = {c: self.tabella.item(riga, j).text()
                for j, c in enumerate(self.COLONNE)}
        return identificativo, dati

    def _apri(self) -> None:
        scelta = self._selezionata()
        if not scelta:
            return
        cartella = scelta[1]["Cartella"]
        if cartella in ("", "—"):
            QMessageBox.information(self, "Archivio",
                                    "Questa lavorazione non ha una cartella.")
            return
        try:
            apri_nel_gestore_file(Path(cartella))
        except FileNotFoundError:
            QMessageBox.warning(self, "Archivio",
                                f"La cartella non esiste più:\n{cartella}")

    def _riesporta(self) -> None:
        scelta = self._selezionata()
        if not scelta:
            return
        identificativo = scelta[0]
        conferma = QMessageBox.question(
            self, "Rigenera",
            "Rigenerare il pacchetto dai modelli originali archiviati?\n"
            "Verrà creata una nuova lavorazione, quella attuale resta invariata.")
        if conferma != QMessageBox.StandardButton.Yes:
            return
        try:
            esito = riesporta(self.archivio, identificativo)
        except Exception as exc:
            QMessageBox.critical(self, "Rigenerazione non riuscita", str(exc))
            return
        self.ricarica()
        if esito.riuscito:
            QMessageBox.information(
                self, "Fatto", f"Nuovo pacchetto in:\n{esito.cartella}")
        else:
            QMessageBox.warning(self, "Con errori", "\n".join(esito.errori))

    def _elimina(self) -> None:
        scelta = self._selezionata()
        if not scelta:
            return
        identificativo, dati = scelta
        conferma = QMessageBox.question(
            self, "Elimina",
            f"Eliminare la lavorazione di {dati['Cliente']} del {dati['Data']}?\n\n"
            "Vengono rimossi anche i file generati nella sua cartella.\n"
            "I modelli originali restano in archivio.")
        if conferma != QMessageBox.StandardButton.Yes:
            return
        self.archivio.elimina_lavorazione(identificativo, cancella_file=True)
        self.ricarica()
