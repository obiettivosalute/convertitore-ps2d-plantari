# Roadmap

## Adesso — la prova di import, secondo giro

Il primo tentativo si è fermato al caricamento dei layer. Due pacchetti sono
in prova presso il tecnico — CONTROLLO FORMATO e PROVA IMPORT — e il
confronto fra i loro esiti dice da che parte guardare. Vedi
[[Import rifiutato - indagine]].

Se servisse il terzo giro, conviene scrivere uno strumento che generi in un
colpo solo la serie dei pacchetti ibridi: si parte da quello di controllo e
si sostituisce **un layer alla volta** con quello generato, così una sola
consegna copre tutte le combinazioni invece di sei giri di posta. Il primo
layer da mettere alla prova è l'`.obj`.

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

## Eventualmente, se la prova V1 va male

**Superficie pre-compensata.** Se la fresa aggiunge spessore al modello
caricato, generare la superficie meno quello spessore.

**Formati alternativi.** Se il software accetta STL o altro come geometria
finita, saltare del tutto il PS2D per la lavorazione e tenerlo solo per
l'archivio.

---

## Collegamenti

- [[Verifiche aperte]]
- [[Status componenti]]
- [[Modello dati]]
