"""Anagrafica clienti: consultazione e modifica dei dati."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView,
                             QLabel, QLineEdit, QMessageBox, QPushButton,
                             QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)

from src.db import Archivio


class SchedaClienti(QWidget):
    """Elenco dei clienti, con modifica in linea dei campi anagrafici."""

    COLONNE = ["Cognome", "Nome", "Data nascita", "Email", "Telefono", "Note"]
    CAMPI = ["cognome", "nome", "data_nascita", "email", "telefono", "note"]

    cliente_modificato = pyqtSignal()

    def __init__(self, archivio: Archivio, parent=None):
        super().__init__(parent)
        self.archivio = archivio
        self._in_ricarica = False

        disposizione = QVBoxLayout(self)
        barra = QHBoxLayout()
        self.filtro = QLineEdit()
        self.filtro.setPlaceholderText("cerca per cognome, nome o data di nascita")
        self.filtro.textChanged.connect(self.ricarica)
        bottone = QPushButton("Aggiorna")
        bottone.clicked.connect(self.ricarica)
        barra.addWidget(self.filtro, 1)
        barra.addWidget(bottone)
        disposizione.addLayout(barra)

        self.tabella = QTableWidget(0, len(self.COLONNE))
        self.tabella.setHorizontalHeaderLabels(self.COLONNE)
        self.tabella.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabella.verticalHeader().setVisible(False)
        self.tabella.itemChanged.connect(self._salva_modifica)
        self.tabella.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch)
        disposizione.addWidget(self.tabella, 1)

        nota = QLabel("Le modifiche si salvano appena si esce dalla cella. "
                      "Cognome, nome e data di nascita finiscono nei file "
                      "generati: correggerli qui non cambia i pacchetti già creati.")
        nota.setWordWrap(True)
        nota.setStyleSheet("color:#666; font-size:11px;")
        disposizione.addWidget(nota)

        self.ricarica()

    def ricarica(self) -> None:
        self._in_ricarica = True
        clienti = self.archivio.elenca_clienti(self.filtro.text())
        self.tabella.setRowCount(len(clienti))
        for i, c in enumerate(clienti):
            valori = [c.cognome, c.nome, c.data_nascita, c.email, c.telefono, c.note]
            for j, v in enumerate(valori):
                voce = QTableWidgetItem(v)
                if j == 0:
                    voce.setData(Qt.ItemDataRole.UserRole, c.id)
                self.tabella.setItem(i, j, voce)
        self.tabella.resizeColumnsToContents()
        self._in_ricarica = False

    def _salva_modifica(self, voce: QTableWidgetItem) -> None:
        if self._in_ricarica:
            return
        riga, colonna = voce.row(), voce.column()
        identificativo = self.tabella.item(riga, 0).data(Qt.ItemDataRole.UserRole)
        if identificativo is None:
            return
        campo = self.CAMPI[colonna]
        valore = voce.text().strip()
        if campo in ("cognome", "nome") and not valore:
            QMessageBox.warning(self, "Dato obbligatorio",
                                f"Il campo {campo} non può restare vuoto.")
            self.ricarica()
            return
        self.archivio.aggiorna_cliente(identificativo, **{campo: valore})
        self.cliente_modificato.emit()
