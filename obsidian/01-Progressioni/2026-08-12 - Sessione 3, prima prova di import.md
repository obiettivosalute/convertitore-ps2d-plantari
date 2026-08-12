# 2026-08-12 — Terza sessione: la prima prova di import

## Dove siamo arrivati

Il gestionale è completo e collaudato: converte, archivia, genera i
pacchetti. La geometria è verificata con scarti di due centesimi di
millimetro. Quello che manca non è codice — è la conferma che il software
dell'azienda accetti quello che produciamo.

La prima prova ha dato un risultato **parziale ma ricco**:

1. lo ZIP viene accettato in importazione — **sì**
2. il paziente compare in elenco, corretto — **sì**
3. le immagini si aprono — **no**: *«La scansione non può essere aperta!»*

I primi due passi valgono più di quanto sembri. Escludono l'intero
involucro — nome dell'archivio, `manifest.json`, i due ZIP annidati, i nomi
dei file — e dimostrano che il `.his` viene letto e interpretato, altrimenti
il paziente non esisterebbe con i suoi dati. Resta il caricamento dei layer.

## Cosa ha detto il confronto

Confrontando file per file il pacchetto generato con l'originale, il dato
più importante è quello che **non** differiva: `.sca` e `.ima` sono
byte-compatibili, identici in dimensione e header salvo il fattore di quota,
che è un valore calcolato. La mappa quote — la geometria vera — era già
scritta correttamente fin dall'inizio.

Le differenze stavano tutte nei layer accessori e nei dettagli di forma:
terminatori CRLF invece di LF nel `.his` e nell'`.obj`, un a capo di troppo
nel `.his`, la riga finale `# End of file.` assente dall'`.obj`, il chunk
`pHYs` mancante nel PNG, i segmenti EXIF mancanti nel JPEG, i layer
raggruppati per piede nello ZIP quando negli originali non lo sono.

Il sospetto principale resta l'`.obj` senza `# End of file.`: se il lettore
usa quella riga per riconoscere un file completo, lo scarta come troncato — e
la scansione risulta non apribile pur essendo tutto il resto in ordine.

Dettagli completi in [[Import rifiutato - indagine]].

## L'errore che ho fatto e come è saltato fuori

Il primo tentativo di aggiungere il chunk `pHYs` non ha funzionato per
niente: Pillow scarta i chunk che gestisce da sé, e va invece passato `dpi`
al salvataggio. Il codice sembrava corretto e non dava errori. Se ne è
accorto solo il controllo sul file effettivamente prodotto.

Vale come promemoria: su un formato ricostruito per reverse engineering,
l'unica verifica che conta è rileggere il file scritto, non rileggere il
codice che lo scrive.

## In attesa — cosa succede alla ripresa

Due pacchetti sono stati consegnati al tecnico, da provare **in
quest'ordine**:

1. **CONTROLLO FORMATO (02.02.2000)** — layer originali intatti, cambiano
   solo nomi e anagrafica.
2. **PROVA IMPORT (01.01.2000)** — rigenerato con tutte le correzioni.

Alla ripresa, la prima cosa da chiedere è **quale dei due** ha prodotto quale
esito. Da lì:

| Controllo | Prova | Da fare |
|---|---|---|
| si apre | si apre | risolto: chiudere [[Verifiche aperte\|V1]] e passare allo scanner |
| si apre | non si apre | procedere per sostituzioni: partire dal pacchetto di controllo e rimpiazzare **un layer alla volta** con quello generato, finché non si rompe. Il primo da provare è l'`.obj` |
| non si apre | — | il problema è nei nomi dei file o nell'anagrafica: verificare la marca temporale e i vincoli sui campi. Servirebbe il programma dell'azienda per vedere quali controlli esegue |

Se serve la sostituzione layer per layer, conviene scrivere uno strumento
apposito che generi la serie completa di pacchetti ibridi in un colpo solo:
sei prove invece di sei giri di posta.

## Il resto della coda

Invariato rispetto a prima, e comunque subordinato alla prova di import:
taratura del ritaglio su un calco vero, orientamento predefinito per il nuovo
scanner, fase 2 con l'acquisizione diretta. Vedi [[Roadmap]].

## Collegamenti

- [[Import rifiutato - indagine]]
- [[Verifiche aperte]]
- [[Status componenti]]
- [[Roadmap]]
