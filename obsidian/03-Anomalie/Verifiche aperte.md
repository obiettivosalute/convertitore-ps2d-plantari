# Verifiche aperte

## V1 — Il software accetta i pacchetti che generiamo? *(chiarita in parte)*

**Come funziona davvero il flusso** (chiarito il 12 agosto 2026). Il `.ps2d`
non è il file che va alla fresa: è **l'input del software di modellazione**
fornito dall'azienda. Il programma importa lo ZIP, crea il paziente, apre le
immagini della scansione; la modellazione del plantare avviene lì dentro, e
solo alla fine un pulsante manda il pezzo alla macchina.

**Cosa cade, di conseguenza.** Il timore dello "spessore aggiunto due volte"
non si applica al caso d'uso reale: nel gestionale si caricano **scansioni di
piedi** acquisite con un altro scanner, non plantari già modellati. Il
pacchetto generato contiene quindi la stessa cosa che contengono quelli dello
scanner nativo, e il software fa il lavoro che fa sempre.

**Cosa resta da verificare.** Solo la conformità formale: che il programma
apra senza errori un pacchetto scritto da noi. Non è più una questione di
interpretazione ma di accettazione del file.

**Come verificare.** `strumenti/genera_prova_import.py` costruisce un
pacchetto partendo dalla geometria di una scansione autentica, riletta e
ripassata per intero attraverso il generatore, con anagrafica di fantasia
(PROVA IMPORT, 01.01.2000). Se il software lo apre come apre l'originale, il
formato è validato: stessa geometria, file interamente riscritto da noi.

### Stato: pacchetto consegnato al tecnico il 12 agosto 2026

File inviato: `Obiettivo Salute_Prova-Import_-01.01.2000-12.08.2026-PROVA1.zip`
(1,1 MB, entrambi i piedi). Riproducibile in qualsiasi momento rilanciando lo
strumento sul pacchetto originale.

**Cosa serve sapere al ritorno**, in ordine di importanza:

1. **Lo ZIP viene accettato in importazione?** È la domanda principale. Se
   il programma lo rifiuta subito, il problema è nell'involucro: manifest,
   nome dell'archivio o struttura.
2. **Il paziente PROVA IMPORT compare in elenco?** Se sì, il `.his` è stato
   letto correttamente, quindi nome, cognome e data di nascita passano.
3. **Le immagini si aprono?** Se il paziente c'è ma le immagini no, il
   problema è nei layer: `.sca`, `.ima` o `.farima`.
4. **La forma dei piedi è giusta?** Non capovolta, non deformata, non
   specchiata. Qui si vede se griglia e fattori di scala sono corretti.
5. **Si arriva alla modellazione?** È la conferma definitiva.

Se compare un errore va trascritto **alla lettera**: il messaggio dice quale
campo non torna, e senza quello si procede per tentativi. In quel caso serve
il programma dell'azienda per esaminare quali controlli esegue in lettura.

**Nota sui dati.** Il pacchetto porta l'anagrafica di fantasia, ma la
geometria è quella di una scansione reale: nessun dato identificativo, però
resta un piede vero. Va cancellato dal software a prova conclusa.

---

## V1b — Orientamento delle scansioni di provenienza diversa

Uno scanner diverso da quello nativo può produrre il piede orientato in
un altro verso, e se il modello è il piede intero la **pianta è la faccia
inferiore**, non la superiore: proiettando dall'alto si otterrebbe il dorso.

Nell'interfaccia ci sono quindi la scelta della superficie (predefinita:
pianta del piede), la rotazione a passi di 90° e la specchiatura, separate
per lato. L'anteprima serve proprio a questo: l'arco deve risultare
**rilevato**, non incavato, e la punta orientata come nelle scansioni native.

Da capire alla prima prova con lo scanner reale: quale combinazione è quella
giusta. Una volta trovata, conviene renderla predefinita in `config.py`.

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
