# Roadmap

## Fatto — la prova di import *(13 agosto 2026)*

Il formato è validato: un pacchetto scritto interamente da noi si apre e
arriva alla modellazione. Il guasto era il `.farima`, isolato con la serie
dei pacchetti ibridi. Vedi [[Import rifiutato - indagine]].

**Da qui in avanti il progetto non dipende più dal software della fresa,
ma dallo scanner**, che non è ancora stato acquistato.

---

## Adesso — cosa si può fare senza scanner

Il gestionale è completo e il formato è chiuso, quindi tutto ciò che resta
o aspetta l'hardware o sta nella sezione «cose utili a prescindere» più
sotto. Se si vuole avanzare subito, quelle sono le voci da prendere.

Una manutenzione minore, emersa oggi: `tests/test_flusso.py` scrive i
pacchetti generati nell'archivio vero, lasciando una cartella cliente
finta `Rossi_Mario_15.03.1975` a ogni esecuzione. Il database lo crea già
in una cartella temporanea; converrebbe farlo anche per i file.

---

## Quando arriva lo scanner

**Trovare la combinazione giusta di orientamento** per quel modello di
scanner: superficie, rotazione, specchiatura. Il riconoscimento automatico
del verso guida la scelta; una volta trovata, va resa predefinita in
`config.py` così non si reimposta ogni volta.

**Verificare il ritaglio su un calco vero.** Le soglie attuali (piano su
almeno il 12% dell'area, impronta di almeno 100 cm², scarto entro il 70%)
sono tarate sul piede sinistro del pacchetto di riferimento, che è un piede
appoggiato, non un calco in schiuma. Sul calco reale il piano sarà più
esteso e più netto, quindi il riconoscimento dovrebbe risultare più facile,
ma le soglie vanno riviste sui primi casi.

**Fase 2 — acquisizione dal gestionale.** L'obiettivo è tornare al gesto di
prima: nominativo, scelta del piede, un clic e via. Quasi nessuno scanner di
fascia consumer offre un SDK per pilotarlo dall'esterno, ma tutti salvano in
una cartella: il gestionale può sorvegliarla e importare da solo il file
appena compare. Serve sapere marca, modello e cartella di esportazione.

Pista nuova, dal 13 agosto: paro360 prevede nativamente un'**API
RemoteScan** (`api.schemas.cadenas.de/pcs/commands/remotescan`) e il suo
schema dei moduli mostra un «Paroscan REMOTE, other location». Riguarda il
loro scanner, non uno di terze parti, ma se un giorno si volesse dialogare
con il sistema della fresa invece di limitarsi a produrre file, è da lì che
si comincia. I moduli parlano su porte note: 2050 il servizio e la
modellazione, 2020 il Paromanager, 2025 paroadm, 2080 il webserver, 5432
PostgreSQL.

---

## Poi — cose utili a prescindere

**Aggancio a `prese misure`.** Leggere l'anagrafica del gestionale esistente
in sola lettura, per non reinserire clienti già noti. Il modello dati è già
predisposto.

**Esportazione in serie.** Una modalità da riga di comando che converta una
cartella di modelli, utile quando arrivano più lavorazioni insieme.

**Confronto fra due lavorazioni.** Sovrapporre le mappe quote di plantari
successivi dello stesso cliente, per vedere cosa è cambiato fra un rinnovo e
l'altro.

**Scheda di lavorazione stampabile.** PDF con anteprima e misure, da allegare
alla busta del laboratorio. Il progetto `prese misure` ha già i moduli
`genera_*.py` da cui prendere impostazione e intestazione.

---

## ~~Eventualmente, se la prova V1 va male~~ *(non serve più)*

V1 è passata il 13 agosto 2026, quindi questi due piani di riserva
decadono. Restano annotati perché descrivono alternative reali, se un
domani il quadro cambiasse.

**Superficie pre-compensata.** Se la fresa aggiunge spessore al modello
caricato, generare la superficie meno quello spessore. *Non si applica: nel
caso d'uso reale si caricano scansioni di piedi, non plantari modellati.*

**Formati alternativi.** Se il software accetta STL o altro come geometria
finita, saltare del tutto il PS2D per la lavorazione e tenerlo solo per
l'archivio. *Non serve, il PS2D funziona.*

---

## Da approfondire, senza fretta

**Il `.psc`, formato di scansione attuale.** Il registro dei formati di
paro360 dice che il `.ps2d` che scriviamo è la versione **legacy v6**;
l'equivalente corrente è `.psc` (*paro360 Scan Project*), anch'esso ZIP, con
`.pscc` come contenitore. Il legacy funziona e non c'è motivo di cambiare
oggi, ma se un aggiornamento del software lo dismettesse, è lì che bisogna
guardare.

**L'`.ima` può essere un BMP.** Il registro dichiara per quel layer due
magic: `PCIM001` **oppure** `BM`, cioè un bitmap di Windows normale. Non
serve, ma è una via alternativa se un giorno l'header proprietario desse
problemi.

**L'export plantari `.p3dp`.** Esiste un formato dedicato (*paro360 Insole
Export*) di cui non sappiamo nulla. Potrebbe essere la strada per riportare
in archivio il plantare **modellato**, non solo la scansione di partenza.

---

## Collegamenti

- [[Verifiche aperte]]
- [[Status componenti]]
- [[Modello dati]]
