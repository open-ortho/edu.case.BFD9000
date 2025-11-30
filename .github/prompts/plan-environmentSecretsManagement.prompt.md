## Plan: Gestione Ambienti e Secret (Dev vs Prod)

Questo piano stabilisce una separazione netta tra configurazione di sviluppo e produzione, garantendo che nessun dato sensibile finisca nel repository (Git) e facilitando il deployment.

### Steps
1.  **Generazione Secret Key**
    *   Eseguiremo un comando Python one-liner per generare una chiave crittografica sicura (50 caratteri) da usare subito in locale.
2.  **Creazione `.env` (Locale - Ignorato)**
    *   Creazione del file `.env` con i valori reali per lo sviluppo: `DEBUG=True`, la `SECRET_KEY` generata e `ALLOWED_HOSTS=localhost`.
3.  **Creazione `.env.example` (Template - Committato)**
    *   Creazione di un file "scheletro" con le sole chiavi (es. `SECRET_KEY=change-me`) da committare su Git come guida per altri sviluppatori.
4.  **Sicurezza Git (`.gitignore`)**
    *   Aggiornamento di `.gitignore` per escludere tassativamente il file `.env` dal versionamento.
5.  **Integrazione Docker**
    *   Aggiornamento di `docker-compose.yml` per leggere le variabili dal file `.env` (tramite `env_file`) invece di averle scritte in chiaro.

### Further Considerations
1.  **Produzione**: Sul server finale, dovrai solo creare manualmente un file `.env` con `DEBUG=False` e una chiave diversa.
2.  **Validazione**: Verificheremo che Docker legga correttamente le variabili avviando il container.
