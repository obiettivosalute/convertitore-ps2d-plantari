# 2026-08-12 — Seconda sessione: perché il gestionale esiste

## Il contesto, finalmente chiaro

Il laboratorio aveva uno scanner 3D riconosciuto dal software dell'azienda
fornitrice: si inseriva il nominativo, si sceglieva piede destro o sinistro,
si attivava la videocamera 3D e si acquisiva **la sola superficie plantare**.
Da lì usciva il `.ps2d`.

Lo scanner si è rotto e non è riparabile. Il software esiste ancora ma non
serve a nulla, perché non trova più la periferica: senza scanner non produce
più pacchetti, e senza pacchetti non si arriva alla modellazione.

Il gestionale prende il posto di quel pezzo di catena. Non aggiunge un
passaggio: ne sostituisce uno che si è rotto.

**Il flusso previsto.** Scanner nuovo (ancora da acquistare) → scansione del
**calco in schiuma** di destro e sinistro → import nel gestionale → ZIP con
il `.ps2d` → software di modellazione, dove il lavoro prosegue come sempre.

## Cosa cambia rispetto a quanto ipotizzato prima

Che si scansioni un calco e non il piede ha una conseguenza diretta: il calco
è il **negativo** dell'impronta, quindi la mappa quote va invertita. Il
programma lo gestisce con la scelta della superficie, e il riconoscimento
automatico del verso conferma se è quella giusta.

La conseguenza meno ovvia è che **entra anche il blocco di schiuma**: la
superficie piana attorno all'impronta verrebbe acquisita come geometria
valida. È esattamente il difetto che ha il piede sinistro del pacchetto di
riferimento, dove il vecchio scanner ha ripreso anche il piano d'appoggio.

Averlo già nei dati ha permesso di scrivere e collaudare il ritaglio prima
ancora che lo scanner sia stato comprato.

## Cosa si è costruito

**Riconoscimento del verso.** Le zone di appoggio sono tante e vicine al
sensore, l'arco è poco e lontano: la distribuzione delle quote è nettamente
asimmetrica. 81% dell'area nella metà alta e asimmetria −1,31 sul riferimento
autentico, contro 19% e +1,31 con l'asse rovesciato. In mezzo resta una
fascia in cui il programma dichiara di non sapere.

**Ritaglio del piano.** Il piano si riconosce come grande area a quota quasi
costante nella parte bassa della mappa; si tiene la componente connessa
maggiore sopra di esso. Sul piede sinistro toglie il 43% dell'acquisito e la
lunghezza torna da 295 mm (taglia 45, falsa) a 254 mm, coerente con il destro
(249 mm). Sul destro, già pulito, non interviene.

## L'inciampo utile della sessione

Il ritaglio, appena scritto, ha buttato via il **78%** dei plantari sintetici
del test di flusso: la loro base piatta somiglia a un piano d'appoggio. Un
falso allarme emerso solo perché il test usa modelli diversi dal caso d'uso
previsto — che è precisamente il motivo per cui vale la pena averlo.

Sono state aggiunte due salvaguardie: non si ritaglia se resterebbero meno di
100 cm², né se si butterebbe via oltre il 70% dell'acquisito, e in entrambi i
casi il programma spiega perché si è fermato. Il test di flusso ora verifica
proprio che il falso allarme non si ripresenti.

## Sullo scanner da comprare

Requisiti confermati con il laboratorio: esporta STL, OBJ e PLY; volume
adeguato; accuratezza dichiarata 0,3 mm, abbondante rispetto ai 0,5 mm per
pixel del formato. La scansione avverrà su calco in schiuma, il che evita il
problema del tracking su pelle e del soggetto che si muove.

## Cosa resta

- Importare il pacchetto di prova nel software di modellazione: è l'unica
  verifica possibile finché non arriva lo scanner. Vedi [[Verifiche aperte]].
- Fase 2, acquisizione diretta dal gestionale: rimandata a quando lo scanner
  sarà stato acquistato, perché dipende da cosa mette a disposizione. La via
  praticabile con qualunque modello è la sorveglianza della cartella di
  esportazione. Vedi [[Roadmap]].

## Collegamenti

- [[Decisioni di design]]
- [[Verifiche aperte]]
- [[Status componenti]]
