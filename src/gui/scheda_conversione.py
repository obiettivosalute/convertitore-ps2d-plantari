"""Scheda principale: anagrafica, caricamento dei due plantari, esportazione."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
                             QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QProgressBar,
                             QPushButton, QSpinBox, QTextEdit, QVBoxLayout,
                             QWidget)

from config import LATO_DX, LATO_SX
from src.db import Archivio
from src.ps2d.mesh2height import ESTENSIONI_SUPPORTATE
from src.servizio import OpzioniConversione, esporta, prepara_lato

from .anteprima import WidgetAnteprima


class ZonaFile(QWidget):
    """Riquadro su cui trascinare il file di un piede."""

    file_scelto = pyqtSignal(str)

    def __init__(self, etichetta: str, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.percorso: Path | None = None

        disposizione = QVBoxLayout(self)
        disposizione.setContentsMargins(0, 0, 0, 0)
        self.bottone = QPushButton(f"Trascina qui il file {etichetta}\no clicca per sceglierlo")
        self.bottone.setMinimumHeight(58)
        self.bottone.setStyleSheet(
            "QPushButton { border: 2px dashed #9ab; border-radius: 6px;"
            " background: #f7fbff; color: #456; }"
            "QPushButton:hover { background: #eef6ff; }")
        self.bottone.clicked.connect(self._scegli)
        disposizione.addWidget(self.bottone)

    def _scegli(self) -> None:
        filtri = "Mesh 3D (" + " ".join(f"*{e}" for e in sorted(ESTENSIONI_SUPPORTATE)) + ")"
        percorso, _ = QFileDialog.getOpenFileName(self, "Scegli il modello 3D", "", filtri)
        if percorso:
            self.imposta(Path(percorso))

    def imposta(self, percorso: Path) -> None:
        self.percorso = Path(percorso)
        self.bottone.setText(f"{self.percorso.name}\n"
                             f"{self.percorso.stat().st_size / 1024:,.0f} KB")
        self.bottone.setStyleSheet(
            "QPushButton { border: 2px solid #3a7; border-radius: 6px;"
            " background: #f2fff8; color: #163; }")
        self.file_scelto.emit(str(self.percorso))

    def pulisci(self, etichetta: str) -> None:
        self.percorso = None
        self.bottone.setText(f"Trascina qui il file {etichetta}\no clicca per sceglierlo")
        self.bottone.setStyleSheet(
            "QPushButton { border: 2px dashed #9ab; border-radius: 6px;"
            " background: #f7fbff; color: #456; }")

    def dragEnterEvent(self, evento: QDragEnterEvent):  # noqa: N802
        if evento.mimeData().hasUrls():
            url = evento.mimeData().urls()[0].toLocalFile()
            if Path(url).suffix.lower() in ESTENSIONI_SUPPORTATE:
                evento.acceptProposedAction()

    def dropEvent(self, evento: QDropEvent):  # noqa: N802
        url = evento.mimeData().urls()[0].toLocalFile()
        self.imposta(Path(url))


class LavoroAnteprima(QObject):
    """Converte un file in un thread separato, per non bloccare la finestra."""

    finito = pyqtSignal(str, object)
    fallito = pyqtSignal(str, str)

    def __init__(self, percorso: Path, lato: str, opzioni: OpzioniConversione):
        super().__init__()
        self.percorso, self.lato, self.opzioni = percorso, lato, opzioni

    def esegui(self) -> None:
        esito = prepara_lato(self.percorso, self.lato, self.opzioni)
        if esito.riuscito:
            self.finito.emit(self.lato, esito)
        else:
            self.fallito.emit(self.lato, esito.errore)


class LavoroEsportazione(QObject):
    """Esegue l'esportazione completa in un thread separato."""

    passo = pyqtSignal(str)
    finito = pyqtSignal(object)
    fallito = pyqtSignal(str)

    def __init__(self, archivio, cliente, sx, dx, opzioni, descrizione, note):
        super().__init__()
        self.archivio, self.cliente = archivio, cliente
        self.sx, self.dx = sx, dx
        self.opzioni, self.descrizione, self.note = opzioni, descrizione, note

    def esegui(self) -> None:
        try:
            esito = esporta(self.archivio, self.cliente, self.sx, self.dx,
                            self.opzioni, self.descrizione, self.note,
                            avanzamento=self.passo.emit)
            self.finito.emit(esito)
        except Exception as exc:
            self.fallito.emit(str(exc))


class SchedaConversione(QWidget):
    """Compilazione anagrafica, caricamento dei modelli, generazione pacchetto."""

    esportazione_completata = pyqtSignal()

    def __init__(self, archivio: Archivio, parent=None):
        super().__init__(parent)
        self.archivio = archivio
        self._thread: QThread | None = None
        self._lavoro = None
        self._in_corso: list[tuple] = []

        principale = QVBoxLayout(self)

        # ---------------------------------------------------- anagrafica
        gruppo_cliente = QGroupBox("Cliente")
        form = QGridLayout(gruppo_cliente)
        self.cognome = QLineEdit()
        self.nome = QLineEdit()
        self.data_nascita = QLineEdit()
        self.data_nascita.setPlaceholderText("GG.MM.AAAA")
        self.data_nascita.setInputMask("99.99.9999")
        self.email = QLineEdit()
        self.telefono = QLineEdit()
        self.ricerca = QComboBox()
        self.ricerca.setEditable(True)
        self.ricerca.setMinimumWidth(280)
        self.ricerca.setPlaceholderText("cerca un cliente già in archivio")
        self.ricerca.activated.connect(self._carica_cliente)

        form.addWidget(QLabel("In archivio"), 0, 0)
        form.addWidget(self.ricerca, 0, 1, 1, 3)
        bottone_nuovo = QPushButton("Svuota")
        bottone_nuovo.clicked.connect(self._svuota_cliente)
        form.addWidget(bottone_nuovo, 0, 4)

        form.addWidget(QLabel("Cognome"), 1, 0)
        form.addWidget(self.cognome, 1, 1)
        form.addWidget(QLabel("Nome"), 1, 2)
        form.addWidget(self.nome, 1, 3)
        form.addWidget(QLabel("Data di nascita"), 2, 0)
        form.addWidget(self.data_nascita, 2, 1)
        form.addWidget(QLabel("Email"), 2, 2)
        form.addWidget(self.email, 2, 3)
        form.addWidget(QLabel("Telefono"), 3, 0)
        form.addWidget(self.telefono, 3, 1)
        self.descrizione = QLineEdit()
        self.descrizione.setPlaceholderText("es. plantare sportivo, rinnovo 2026")
        form.addWidget(QLabel("Descrizione"), 3, 2)
        form.addWidget(self.descrizione, 3, 3)
        principale.addWidget(gruppo_cliente)

        # ---------------------------------------------------- file e anteprime
        gruppo_file = QGroupBox("Modelli dei plantari")
        griglia = QGridLayout(gruppo_file)
        self.zona_sx = ZonaFile("SINISTRO")
        self.zona_dx = ZonaFile("DESTRO")
        self.zona_sx.file_scelto.connect(lambda p: self._aggiorna_anteprima(LATO_SX, p))
        self.zona_dx.file_scelto.connect(lambda p: self._aggiorna_anteprima(LATO_DX, p))
        self.anteprima_sx = WidgetAnteprima("SINISTRO  (Links)")
        self.anteprima_dx = WidgetAnteprima("DESTRO  (Rechts)")
        griglia.addWidget(self.zona_sx, 0, 0)
        griglia.addWidget(self.zona_dx, 0, 1)
        griglia.addWidget(self.anteprima_sx, 1, 0)
        griglia.addWidget(self.anteprima_dx, 1, 1)
        principale.addWidget(gruppo_file, 1)

        # ---------------------------------------------------- opzioni
        gruppo_opzioni = QGroupBox("Parametri di conversione")
        opzioni = QHBoxLayout(gruppo_opzioni)
        form_op = QFormLayout()
        self.risoluzione = QDoubleSpinBox()
        self.risoluzione.setRange(0.1, 2.0)
        self.risoluzione.setSingleStep(0.1)
        self.risoluzione.setValue(0.5)
        self.risoluzione.setSuffix(" mm/pixel")
        self.superficie = QComboBox()
        self.superficie.addItem("pianta del piede (faccia inferiore)", "inferiore")
        self.superficie.addItem("appoggio del plantare (faccia superiore)", "superiore")
        self.superficie.setToolTip(
            "Determina il verso della mappa quote.\n\n"
            "Pianta del piede: per le scansioni della superficie plantare.\n"
            "Faccia superiore: per plantari già modellati e per i calchi in\n"
            "schiuma, che sono il negativo dell'impronta.\n\n"
            "Non serve indovinare: sotto ogni anteprima il programma dice se\n"
            "il verso è giusto. Deve risultare l'appoggio in rosso e l'arco\n"
            "in blu; se è tutto rovesciato, cambia questa voce.")
        self.superficie.currentIndexChanged.connect(self._riconverti)
        self.unita = QComboBox()
        self.unita.addItems(["auto", "mm", "cm", "m"])
        self.unita.currentIndexChanged.connect(self._riconverti)
        form_op.addRow("Risoluzione", self.risoluzione)
        form_op.addRow("Superficie da usare", self.superficie)
        form_op.addRow("Unità del file", self.unita)

        form_op2 = QFormLayout()
        self.frame_standard = QCheckBox("griglia standard 340x684")
        self.frame_standard.setChecked(True)
        self.frame_standard.setToolTip(
            "Usa lo stesso fotogramma dei file prodotti dallo scanner.\n"
            "Togliendo la spunta la griglia si adatta al modello.")
        self.zip_invio = QCheckBox("genera anche lo ZIP di invio")
        self.zip_invio.setChecked(True)
        self.passo_obj = QSpinBox()
        self.passo_obj.setRange(1, 12)
        self.passo_obj.setValue(3)
        self.passo_obj.setToolTip("Passo di campionamento della mesh OBJ, in pixel")
        form_op2.addRow(self.frame_standard)
        form_op2.addRow(self.zip_invio)
        form_op2.addRow("Passo mesh OBJ", self.passo_obj)

        # orientamento, separato per lato: scanner diversi appoggiano il
        # piede in versi diversi, e il software si aspetta punta in alto
        form_or = QFormLayout()
        self.rotazione_sx = QComboBox()
        self.rotazione_dx = QComboBox()
        for combo in (self.rotazione_sx, self.rotazione_dx):
            for gradi in (0, 90, 180, 270):
                combo.addItem(f"{gradi}°", float(gradi))
            combo.currentIndexChanged.connect(self._riconverti)
        self.specchia_sx = QCheckBox("specchia")
        self.specchia_dx = QCheckBox("specchia")
        for spunta in (self.specchia_sx, self.specchia_dx):
            spunta.setToolTip("Ribalta il modello, se lo scanner lo produce "
                              "rovesciato rispetto al lato")
            spunta.stateChanged.connect(self._riconverti)

        riga_sx = QHBoxLayout()
        riga_sx.addWidget(self.rotazione_sx)
        riga_sx.addWidget(self.specchia_sx)
        riga_dx = QHBoxLayout()
        riga_dx.addWidget(self.rotazione_dx)
        riga_dx.addWidget(self.specchia_dx)
        form_or.addRow("Orientamento SX", riga_sx)
        form_or.addRow("Orientamento DX", riga_dx)

        opzioni.addLayout(form_op)
        opzioni.addLayout(form_op2)
        opzioni.addLayout(form_or)
        opzioni.addStretch(1)
        principale.addWidget(gruppo_opzioni)

        # ---------------------------------------------------- azioni
        riga = QHBoxLayout()
        self.avanzamento = QProgressBar()
        self.avanzamento.setVisible(False)
        self.stato = QLabel("")
        self.bottone_genera = QPushButton("Genera pacchetto PS2D")
        self.bottone_genera.setMinimumHeight(38)
        self.bottone_genera.setStyleSheet(
            "QPushButton { font-weight: bold; background:#2d7; color:white;"
            " border-radius:5px; padding: 6px 18px; }"
            "QPushButton:hover { background:#3e8; }"
            "QPushButton:disabled { background:#bbb; }")
        self.bottone_genera.clicked.connect(self._genera)
        riga.addWidget(self.stato, 1)
        riga.addWidget(self.avanzamento)
        riga.addWidget(self.bottone_genera)
        principale.addLayout(riga)

        self.esito = QTextEdit()
        self.esito.setReadOnly(True)
        self.esito.setMaximumHeight(120)
        self.esito.setVisible(False)
        principale.addWidget(self.esito)

        self.ricarica_clienti()

    # ------------------------------------------------------------ anagrafica
    def ricarica_clienti(self) -> None:
        self.ricerca.blockSignals(True)
        self.ricerca.clear()
        self.ricerca.addItem("— nuovo cliente —", None)
        for c in self.archivio.elenca_clienti():
            self.ricerca.addItem(c.etichetta, c.id)
        self.ricerca.setCurrentIndex(0)
        self.ricerca.blockSignals(False)

    def _carica_cliente(self, indice: int) -> None:
        cliente_id = self.ricerca.itemData(indice)
        if cliente_id is None:
            self._svuota_cliente()
            return
        c = self.archivio.cliente(cliente_id)
        if c:
            self.cognome.setText(c.cognome)
            self.nome.setText(c.nome)
            self.data_nascita.setText(c.data_nascita)
            self.email.setText(c.email)
            self.telefono.setText(c.telefono)

    def _svuota_cliente(self) -> None:
        for campo in (self.cognome, self.nome, self.email, self.telefono,
                      self.descrizione):
            campo.clear()
        self.data_nascita.setText("")
        self.ricerca.setCurrentIndex(0)

    # ------------------------------------------------------------ anteprime
    def opzioni_correnti(self) -> OpzioniConversione:
        return OpzioniConversione(
            mm_per_px=self.risoluzione.value(),
            usa_frame_standard=self.frame_standard.isChecked(),
            superficie=self.superficie.currentData(),
            unita=self.unita.currentText(),
            ruota_gradi_sx=self.rotazione_sx.currentData(),
            ruota_gradi_dx=self.rotazione_dx.currentData(),
            specchia_sx=self.specchia_sx.isChecked(),
            specchia_dx=self.specchia_dx.isChecked(),
            passo_obj=self.passo_obj.value(),
            genera_zip_invio=self.zip_invio.isChecked(),
        )

    def _riconverti(self) -> None:
        """Rigenera le anteprime quando cambia un parametro di orientamento."""
        for lato, zona in ((LATO_SX, self.zona_sx), (LATO_DX, self.zona_dx)):
            if zona.percorso:
                self._aggiorna_anteprima(lato, str(zona.percorso))

    def _aggiorna_anteprima(self, lato: str, percorso: str) -> None:
        widget = self.anteprima_sx if lato == LATO_SX else self.anteprima_dx
        widget.pulisci("elaborazione in corso…")
        self.stato.setText(f"lettura {Path(percorso).name}…")

        thread = QThread(self)
        lavoro = LavoroAnteprima(Path(percorso), lato, self.opzioni_correnti())
        lavoro.moveToThread(thread)
        thread.started.connect(lavoro.esegui)
        lavoro.finito.connect(self._anteprima_pronta)
        lavoro.fallito.connect(self._anteprima_fallita)
        lavoro.finito.connect(thread.quit)
        lavoro.fallito.connect(thread.quit)

        # I riferimenti vanno tenuti vivi lato Python finche' il thread gira,
        # altrimenti Qt lo distrugge a meta' lavoro. Cambiando in fretta un
        # parametro si accodano piu' conversioni dello stesso lato: si tiene
        # una lista e si scarta ciascuna quando ha finito davvero.
        coppia = (thread, lavoro)
        self._in_corso.append(coppia)

        def concluso():
            if coppia in self._in_corso:
                self._in_corso.remove(coppia)
            thread.deleteLater()

        thread.finished.connect(concluso)
        thread.start()

    def _anteprima_pronta(self, lato: str, esito) -> None:
        widget = self.anteprima_sx if lato == LATO_SX else self.anteprima_dx
        widget.mostra(esito.risultato)
        if esito.avvisi:
            self.stato.setText("⚠ " + " · ".join(esito.avvisi))
            self.stato.setStyleSheet("color:#a60;")
        else:
            self.stato.setText("modello caricato correttamente")
            self.stato.setStyleSheet("color:#161;")

    def _anteprima_fallita(self, lato: str, errore: str) -> None:
        widget = self.anteprima_sx if lato == LATO_SX else self.anteprima_dx
        widget.pulisci("lettura non riuscita")
        self.stato.setText(f"errore su {lato}: {errore}")
        self.stato.setStyleSheet("color:#b00;")

    # ------------------------------------------------------------ esportazione
    def _valida(self) -> str:
        if not self.cognome.text().strip():
            return "manca il cognome"
        if not self.nome.text().strip():
            return "manca il nome"
        data = self.data_nascita.text().strip()
        if len(data) != 10 or data.count(".") != 2 or not data.replace(".", "").isdigit():
            return "la data di nascita va scritta come GG.MM.AAAA"
        g, m, a = (int(x) for x in data.split("."))
        if not (1 <= g <= 31 and 1 <= m <= 12 and 1900 <= a <= 2100):
            return f"data di nascita non valida: {data}"
        if not (self.zona_sx.percorso or self.zona_dx.percorso):
            return "carica almeno un plantare"
        return ""

    def _genera(self) -> None:
        problema = self._valida()
        if problema:
            QMessageBox.warning(self, "Dati incompleti", problema)
            return

        cliente = self.archivio.trova_o_crea_cliente(
            self.cognome.text(), self.nome.text(), self.data_nascita.text(),
            self.email.text().strip(), self.telefono.text().strip())
        self.archivio.aggiorna_cliente(cliente.id, email=self.email.text().strip(),
                                       telefono=self.telefono.text().strip())

        self.bottone_genera.setEnabled(False)
        self.avanzamento.setVisible(True)
        self.avanzamento.setRange(0, 0)
        self.esito.setVisible(False)

        thread = QThread(self)
        lavoro = LavoroEsportazione(
            self.archivio, cliente,
            self.zona_sx.percorso, self.zona_dx.percorso,
            self.opzioni_correnti(), self.descrizione.text().strip(), "")
        lavoro.moveToThread(thread)
        thread.started.connect(lavoro.esegui)
        lavoro.passo.connect(self._passo)
        lavoro.finito.connect(self._esportazione_finita)
        lavoro.fallito.connect(self._esportazione_fallita)
        lavoro.finito.connect(thread.quit)
        lavoro.fallito.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        self._thread, self._lavoro = thread, lavoro
        thread.start()

    def _passo(self, testo: str) -> None:
        self.stato.setText(testo)
        self.stato.setStyleSheet("color:#345;")

    def _esportazione_finita(self, esito) -> None:
        self.bottone_genera.setEnabled(True)
        self.avanzamento.setVisible(False)
        self.esito.setVisible(True)

        righe = []
        if esito.riuscito:
            self.stato.setText("pacchetto generato")
            self.stato.setStyleSheet("color:#161; font-weight:bold;")
            righe.append(f"Cartella: {esito.cartella}")
            righe.append(f"Pacchetto per la fresa: {Path(esito.ps2d).name}")
            if esito.zip_invio:
                righe.append(f"Archivio di invio: {Path(esito.zip_invio).name}")
        else:
            self.stato.setText("esportazione non riuscita")
            self.stato.setStyleSheet("color:#b00; font-weight:bold;")
        for e in esito.errori:
            righe.append(f"ERRORE — {e}")
        for a in esito.avvisi:
            righe.append(f"avviso — {a}")
        self.esito.setPlainText("\n".join(righe))

        self.ricarica_clienti()
        self.esportazione_completata.emit()

    def _esportazione_fallita(self, errore: str) -> None:
        self.bottone_genera.setEnabled(True)
        self.avanzamento.setVisible(False)
        self.stato.setText("esportazione non riuscita")
        self.stato.setStyleSheet("color:#b00; font-weight:bold;")
        QMessageBox.critical(self, "Errore", errore)
