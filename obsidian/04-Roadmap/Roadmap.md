# Roadmap

## Adesso — la prova di import

Va chiusa [[Verifiche aperte|V1]]: importare nel software di modellazione il
pacchetto prodotto da `strumenti/genera_prova_import.py`. È l'unica verifica
possibile finché non arriva lo scanner, e conferma che i file scritti da noi
siano accettati.

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
