# Roadmap

## Adesso — la prova sulla macchina

Prima di aggiungere qualsiasi cosa va chiusa [[Verifiche aperte|V1]]:
generare un pacchetto da un plantare noto e aprirlo nel software della fresa.
Tutto il resto dipende dall'esito.

Serve anche sapere:

- come si chiama il software della fresa e come importa i file;
- da quale programma escono i plantari e in che formato;
- se esiste un `.ps2d` di esempio già contenente un plantare, accettato dalla
  macchina. Sarebbe il riferimento migliore.

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
