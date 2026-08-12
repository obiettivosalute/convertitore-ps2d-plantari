# Verifiche aperte

## V1 — Come la fresa interpreta un PS2D che contiene un plantare

**La questione.** Il formato PS2D nasce per trasportare la **scansione di un
piede**: è questo che contengono i pacchetti autentici esaminati. Il
gestionale ci mette dentro un **plantare già modellato**. Il file è
formalmente identico, ma il significato di ciò che trasporta è diverso.

Due scenari:

1. il software della fresa tratta il `.ps2d` come geometria da lavorare —
   tutto a posto, il pezzo esce come il modello caricato;
2. lo tratta come piede scansionato e ci costruisce sopra il plantare
   applicando le proprie regole — il file viene letto senza errori ma il
   pezzo esce **diverso**, probabilmente con lo spessore aggiunto due volte.

**Perché non si può risolvere dai file.** Nessuna analisi dei pacchetti può
dire cosa fa il programma che li legge. Serve una prova sulla macchina.

**Come verificare.** Generare un pacchetto da un plantare di forma nota,
aprirlo nel software della fresa e confrontare con il modello di partenza:
altezza dell'arco, spessore al tallone, lunghezza totale. Se il software
mostra il pezzo così com'è, scenario 1. Se propone un plantare da costruire,
scenario 2.

**Se si verifica lo scenario 2.** Le strade sono due: generare la superficie
pre-compensata, sottraendo ciò che il software aggiunge, oppure esportare in
un altro formato accettato dalla macchina. Va deciso dopo la prova, non
prima.

---

## V2 — Griglia di dimensione variabile

Nei due esempi la griglia è 340 × 684 e 342 × 685: **non è fissa**. In
lettura si prende sempre dall'header. In scrittura si usa il valore più
ricorrente, ma non è confermato che la fresa accetti griglie diverse da
quelle che produce il suo scanner. Da chiarire nella stessa prova di V1.

---

## V3 — `Model.mtl` assente

Gli `.obj` dichiarano `mtllib Model.mtl`, ma quel file non è nel pacchetto,
né negli originali né nei generati. Evidentemente il lettore lo ignora. Il
generatore replica la riga per aderenza; se emergesse che serve, basta
aggiungerlo.

---

## V4 — Qualità delle scansioni in ingresso

Nel pacchetto analizzato la scansione del piede **sinistro** include anche il
piano d'appoggio attorno al piede: 63% del fotogramma valido contro il 34%
del destro. Misurando la sagoma grezza il piede risulta 295 × 146 mm (taglia
45); segmentando via il piano si ottiene 253 × 114 mm, coerente con il destro
(249 × 108 mm).

Non riguarda direttamente il gestionale — che lavora su plantari già
modellati, non su scansioni — ma è utile saperlo: se un giorno si importano
scansioni grezze, serve un ritaglio del contorno.

---

## Collegamenti

- [[Decisioni di design]]
- [[Status componenti]]
- [[Roadmap]]
