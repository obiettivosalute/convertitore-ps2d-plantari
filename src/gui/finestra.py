"""Finestra principale del gestionale."""

from __future__ import annotations

from PyQt6.QtWidgets import (QFileDialog, QMainWindow, QMessageBox,
                             QTabWidget)

from config import APP_NOME, APP_VERSIONE, ARCHIVIO_DIR, DATA_DIR
from src.db import Archivio
from src.ps2d import leggi_ps2d

from .ispezione import FinestraIspezione
from .scheda_archivio import SchedaArchivio, apri_nel_gestore_file
from .scheda_clienti import SchedaClienti
from .scheda_conversione import SchedaConversione


class FinestraPrincipale(QMainWindow):
    def __init__(self, archivio: Archivio | None = None):
        super().__init__()
        self.archivio = archivio or Archivio()
        self.setWindowTitle(f"{APP_NOME}  v{APP_VERSIONE}")
        self.resize(1180, 900)

        self.schede = QTabWidget()
        self.scheda_conversione = SchedaConversione(self.archivio)
        self.scheda_archivio = SchedaArchivio(self.archivio)
        self.scheda_clienti = SchedaClienti(self.archivio)

        self.schede.addTab(self.scheda_conversione, "Nuova lavorazione")
        self.schede.addTab(self.scheda_archivio, "Archivio")
        self.schede.addTab(self.scheda_clienti, "Clienti")
        self.setCentralWidget(self.schede)

        self.scheda_conversione.esportazione_completata.connect(
            self.scheda_archivio.ricarica)
        self.scheda_conversione.esportazione_completata.connect(
            self.scheda_clienti.ricarica)
        self.scheda_clienti.cliente_modificato.connect(
            self.scheda_conversione.ricarica_clienti)

        self._costruisci_menu()
        self.statusBar().showMessage(f"archivio: {DATA_DIR}")

    def _costruisci_menu(self) -> None:
        menu_file = self.menuBar().addMenu("&File")
        menu_file.addAction("Apri la cartella archivio", self._apri_archivio)
        menu_file.addAction("Ispeziona un pacchetto PS2D…", self._ispeziona)
        menu_file.addSeparator()
        menu_file.addAction("Esci", self.close)

        menu_aiuto = self.menuBar().addMenu("&?")
        menu_aiuto.addAction("Informazioni", self._informazioni)

    def _apri_archivio(self) -> None:
        try:
            apri_nel_gestore_file(ARCHIVIO_DIR)
        except FileNotFoundError:
            QMessageBox.warning(self, "Archivio", "Cartella non trovata.")

    def _ispeziona(self) -> None:
        percorso, _ = QFileDialog.getOpenFileName(
            self, "Scegli un pacchetto", "",
            "Pacchetti PS2D (*.ps2d *.zip);;Tutti i file (*)")
        if not percorso:
            return
        try:
            contenuto = leggi_ps2d(percorso)
        except Exception as exc:
            QMessageBox.critical(self, "Lettura non riuscita", str(exc))
            return

        finestra = FinestraIspezione(contenuto, self)
        finestra.show()

    def _informazioni(self) -> None:
        QMessageBox.about(
            self, "Informazioni",
            f"<b>{APP_NOME}</b><br>versione {APP_VERSIONE}<br><br>"
            "Converte i modelli 3D dei plantari nel formato PS2D letto dal "
            "software della fresa e tiene l'archivio delle lavorazioni.<br><br>"
            "Il formato è stato ricostruito analizzando i pacchetti prodotti "
            "dallo scanner: vedi <i>docs/FORMATO_PS2D.md</i>.<br><br>"
            "I dati dei clienti restano su questo computer, "
            f"in <i>{DATA_DIR}</i>.")
