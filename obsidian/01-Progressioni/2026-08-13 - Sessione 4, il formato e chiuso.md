# 2026-08-13 — Quarta sessione: il formato è chiuso

## Dove siamo arrivati

Il software di modellazione apre un pacchetto scritto interamente da noi,
carica entrambi i piedi, li mostra orientati correttamente e arriva alla
pagina di modellazione. **La verifica V1 è chiusa.** Quello che mancava non
era codice ma una convenzione, e adesso si sa qual era.

Il colpevole era il `.farima`, per due difetti insieme: il PNG va scritto
**capovolto** rispetto al `.sca`, e il suo chunk `pHYs` deve dichiarare la
scala vera della griglia — 2000 pixel per metro — non un valore di comodo.

## Il riscontro del tecnico sui due pacchetti

CONTROLLO FORMATO ha superato **tutti e cinque** i passi, fino alla
modellazione. PROVA IMPORT si è fermato al terzo, con lo stesso messaggio
della volta prima.

Il controllo portava i layer originali ma nomi e anagrafica riscritti da
noi, quindi quell'esito ha assolto in un colpo solo il nome dell'archivio,
il `manifest.json`, la struttura dei due ZIP annidati, i nomi dei file, la
marca temporale e — cosa che non era ancora certa — **il `.his` come lo
scriviamo**. Restavano solo i layer.

## La serie degli ibridi

È stata la strada indicata dalla tabella di ieri, e ha funzionato al primo
colpo. `strumenti/genera_prove_ibride.py` parte dal pacchetto di controllo
e ne sforna una copia per ciascun layer, sostituendo **quel solo layer**
con la nostra versione. Sei pacchetti in una consegna sola, con anagrafiche
diverse perché il tecnico li distinguesse in elenco.

| Ibrido | Esito |
|---|---|
| `.sca` nostro | si apre |
| `.ima` nostro | si apre |
| `.bmp` nostro | si apre |
| `.obj` nostro | si apre |
| `.farima` nostro | **non si apre** |
| tutti nostri, con `.bmp` riallineato | **non si apre** |

Un solo layer colpevole, isolato senza ambiguità. E il sesto pacchetto ha
confermato per esclusione: conteneva il nostro `.farima`, quindi il `.bmp`
non c'entrava nulla.

## La diagnosi

Nei file autentici il canale alfa del `.farima` ha **lo stesso numero** di
pixel opachi della maschera del `.sca` — 146.020 sul sinistro — ma in
posizioni diverse. La trasformazione che le fa combaciare è esattamente il
capovolgimento delle righe. Noi lo scrivevamo nello stesso verso del
`.sca`: il software legge i due layer con convenzioni opposte, la maschera
non torna, e la scansione risulta non apribile.

La trappola è che **la convenzione non è uniforme fra i layer**: l'`.ima`
va invece nello stesso verso del `.sca`, verificato su entrambi i piedi di
entrambi i pacchetti. È il motivo per cui la cosa non era emersa prima.

Il secondo difetto stava nel `pHYs`: l'originale dichiara 2000 px/m, che è
mille millimetri diviso il passo da 0,5 mm — la scala fisica reale. Noi
scrivevamo 2835, cioè il default di Pillow per 72 dpi, un numero senza
significato.

## Le correzioni

In `src/ps2d/writer.py`: `genera_farima()` restituisce l'immagine
capovolta, e il `pHYs` si ricava dalla griglia con la nuova
`pixel_per_metro()`. Rigenerata la prova, il `.farima` combacia con
l'originale su entrambe le convenzioni e su entrambi i piedi.

Il secondo giro — l'ibrido col solo `.farima` corretto e la prova completa
— si è aperto tutto, e la schermata di modellazione mostra i due piedi con
punta e arco al posto giusto, niente capovolgimenti né specchiature.

## Errori e vicoli ciechi

**Il sospetto principale di ieri era sbagliato.** L'`.obj` senza
`# End of file.` sembrava il candidato naturale, ed era già stato corretto:
il file ora apre con `# Generated.`, chiude con `# End of file.` e non ha
un solo CRLF. Falliva lo stesso. L'ibrido con il solo `.obj` nostro si è
aperto senza problemi.

**Una correzione di ieri ci aveva allontanati dall'originale.**
Aggiungendo l'EXIF al `.bmp` gli è stata scritta anche una densità in dpi
(`units=1`) che l'originale non dichiara (`units=0`). Sembrava una pista;
non lo era — l'ibrido col nostro `.bmp` si apre. La modifica è stata
lasciata dov'è proprio perché innocua.

**La specifica conteneva due affermazioni false**, scritte guardando il
nostro output invece dell'originale: che l'alfa del `.farima` coincide con
la maschera del `.sca` (coincide solo capovolto) e che il `pHYs` sta a
72 dpi. Corrette in `docs/FORMATO_PS2D.md`. È lo stesso errore di metodo
annotato ieri: verificare il file prodotto, non il codice che lo scrive —
e nemmeno la documentazione che abbiamo scritto noi.

**`tests/test_flusso.py` scrive nell'archivio vero.** Il database è
temporaneo, ma i pacchetti generati finiscono in `data/archivio/`: ogni
esecuzione lascia una cartella cliente finta `Rossi_Mario_15.03.1975`. Le
residue sono state cancellate, ma il test continuerà a produrne.

## Il programma della fresa

Il tecnico ha reso disponibile l'installazione di **paro360**, 9,5 GB. È
un'applicazione Qt/C++ nativa del fornitore CADENAS, quindi non
ispezionabile per decompilazione, ma porta un registro MIME dei formati —
`data/mime/packages/paromed.xml` — che li documenta con i magic number. Il
reverse engineering ne esce confermato: `.sca` → `PCSC001`, `.ima` →
`PCIM001`, `.ps2d` = *paroContour System Scan Project*.

Quattro cose che non sapevamo:

- il `.ps2d` è il formato **legacy v6**; l'equivalente attuale è `.psc`
  (*paro360 Scan Project*, anch'esso ZIP), con `.pscc` come contenitore
- l'`.ima` accetta **anche un BMP di Windows** normale: il registro
  dichiara `PCIM001` **oppure** `BM`
- esiste un export dedicato ai plantari, `.p3dp`
- esiste un'**API RemoteScan** (`api.schemas.cadenas.de/pcs/commands/remotescan`)
  e lo schema dei moduli mostra un «Paroscan REMOTE, other location»:
  l'acquisizione remota è prevista nativamente. Per la fase 2 potrebbe
  esserci una strada documentata invece della sorveglianza di una cartella

L'architettura: PostgreSQL sulla 5432 (`parodb1`, `parodb2`), un servizio
sulla 2050 che è anche la porta del modulo Modellazione, un webserver
`tini.exe` sulla 2080 con cgi-bin, Paromanager sulla 2020 (2015 legacy),
paroadm sulla 2025.

I manuali e il registro dei formati sono stati copiati in
`Desktop\paro360 - documentazione\` (22 MB); il resto dell'installazione
viene cancellato.

## Il resto della sessione

**Ispezione dei pacchetti riscritta.** La voce «Ispeziona un pacchetto
PS2D» mostrava cinque righe. Ora apre una finestra a sei schede —
Riepilogo, File, Anagrafica, Manifest, Geometria, Anteprime — con
esportazione del report in `.txt` o `.json`. Il nuovo modulo è
`src/gui/ispezione.py`; il lettore in `src/ps2d/reader.py` conserva quello
che già raccoglieva e ne aggiunge l'inventario dei file, e `report()`,
`report_dati()` e `osservazioni()` producono il resoconto. Quest'ultima
segnala da sola le difformità che si è imparato a cercare: griglie diverse
fra i piedi, copertura del fotogramma sopra il 50%, layer mancanti, `.his`
divergenti.

**L'ambiente era rotto.** `python main.py` non apriva niente: mancavano
`scipy` e `trimesh`, e l'errore restava invisibile perché con il doppio
clic l'applicazione parte sotto `pythonw.exe`, che non ha console.
Installate le librerie, e `main.py` ora controlla **tutte** le dipendenze
prima di toccare `src.gui`, mostrando l'elenco di quelle mancanti in una
finestra di dialogo oltre che a video.

**Due comandi di sessione**, `/apriscanner3d` e `/chiudiscanner3d`, in
`C:\Users\Administrator\.claude\commands\`.

## Cosa succede alla ripresa

Il formato è validato: non ci sono più domande aperte sul software di
modellazione. Il lavoro torna a dipendere dallo scanner, che non è ancora
stato acquistato.

Restano due verifiche, entrambe da fare sul campo: [[Verifiche aperte|V1b]]
sull'orientamento delle scansioni di provenienza diversa, e
[[Verifiche aperte|V2]] sulla tolleranza alle griglie di dimensione
diversa — anche se il pacchetto autentico ne porta già due diverse fra i
due piedi, 340×684 e 342×685, e si apre senza storie: è un indizio forte
che la griglia non sia vincolata.

Se nel frattempo si vuole avanzare senza scanner, le cose utili a
prescindere stanno in [[Roadmap]]. La pista `.psc` e quella dell'API
RemoteScan sono nuove e valgono un approfondimento quando si arriva alla
fase 2.

## Collegamenti

- [[Import rifiutato - indagine]]
- [[Verifiche aperte]]
- [[Status componenti]]
- [[Roadmap]]
- [[2026-08-12 - Sessione 3, prima prova di import]]
