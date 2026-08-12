"""Configurazione globale del gestionale plantari.

Tutti i parametri del formato PS2D sono stati ricavati per reverse engineering
da pacchetti reali prodotti dallo scanner. Vedi docs/FORMATO_PS2D.md.
"""

from pathlib import Path

# ---------------------------------------------------------------- percorsi
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ARCHIVIO_DIR = DATA_DIR / "archivio"      # pacchetti generati, per cliente
UPLOAD_DIR = DATA_DIR / "originali"       # copia dei file caricati
DB_PATH = DATA_DIR / "plantari.db"
LOG_DIR = DATA_DIR / "log"

for _d in (DATA_DIR, ARCHIVIO_DIR, UPLOAD_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- clinica
# Valori predefiniti. Quelli veri stanno in config_locale.py, che non viene
# versionato: practitionerId e UDID identificano il centro e il dispositivo
# presso il portale, e non hanno motivo di stare in un repository pubblico.
CLINICA_NOME = "Obiettivo Salute"
PRACTITIONER_ID = 0
CLIENT_DEVICE_UDID = "00000000-0000-0000-0000-000000000000"

try:
    from config_locale import *          # noqa: F401,F403
except ImportError:
    pass

# ---------------------------------------------------------------- formato PS2D
# Griglia standard osservata nei file dello scanner: 0,5 mm per pixel.
PIXEL_MM_X = 0.5
PIXEL_MM_Y = 0.5

# Dimensioni del fotogramma. Gli esempi reali usano 340x684 e 342x685 px,
# cioe' circa 170 x 342 mm: la griglia non e' rigidamente fissa, ma resta
# in quell'ordine di grandezza. Usiamo il valore piu' ricorrente.
FRAME_W = 340
FRAME_H = 684

# Riquadro entro cui lo scanner esporta la mesh OBJ (mm), centrato sull'origine.
OBJ_FRAME_W_MM = 141.0
OBJ_FRAME_H_MM = 321.0

# Valori di sfondo / fondo scala
SFONDO_SCA = 0xFFFF      # nessun dato nella mappa quote
SFONDO_IMA = 0xFF        # bianco nell'immagine 8 bit

# Etichette dei lati come le scrive lo scanner (tedesco)
LATO_SX = "Links"
LATO_DX = "Rechts"

# ---------------------------------------------------------------- conversione
# Margine (mm) lasciato attorno al modello quando lo si centra nel fotogramma
MARGINE_MM = 8.0

# Quota di sicurezza: se la mesh e' piu' alta del fondo scala a 16 bit
# non c'e' problema (la risoluzione si adatta), ma sotto questa soglia
# in mm consideriamo il modello sospetto e avvisiamo l'utente.
ALTEZZA_MINIMA_ATTESA_MM = 5.0
ALTEZZA_MASSIMA_ATTESA_MM = 90.0

# Lunghezza plausibile di un plantare, per il controllo qualita'
LUNGHEZZA_MIN_MM = 150.0
LUNGHEZZA_MAX_MM = 340.0

# ---------------------------------------------------------------- interfaccia
APP_NOME = "Gestionale Plantari — Convertitore PS2D"
APP_VERSIONE = "1.0.0"
