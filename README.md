# syncom

Semplice script per scaricare periodicamente i comunicati da nuvola.madisoft.it

# Utilizzo
```
syncom git-source
Copyright (C) 2021 Antonio Napolitano

usage: syncom.py [-h] [-d directory] [-c nome url] [-l log_file] [-v] USER PASS

Semplice script per scaricare periodicamente i comunicati da nuvola.madisoft.it

positional arguments:
  USER           nome utente per il registro
  PASS           password per il registro

optional arguments:
  -h, --help     show this help message and exit
  -d directory   directory dove salvare i comunicati (default: .)
  -c nome url    categoria di comunicati
  -l log_file    file di log
  -v, --verbose  output verboso
```

## Esempio
```
./syncom.py -v -l "output.log" "test-user" "password" -c "comunicati-studenti" "https://nuvola.madisoft.it/bacheca-digitale/bacheca/XXXXXXX/N/NNNNNNN" -d "./comunicati"
```

# Compilazione
Installare [docker](docker.com) ed eseguire i due seguenti comandi nella cartella del repository:
```
docker run -v "$(pwd):/src/" cdrx/pyinstaller-linux
```
```
docker run -v "$(pwd):/src/" --entrypoint /bin/sh cdrx/pyinstaller-windows -c "apt-get update -y && apt-get install -y git && cd /src && git describe --always --dirty --tags > /tmp/version && /entrypoint.sh"
```
Dopodiché si potranno trovare gli eseguibili per linux e per windows nella cartella `dist`.
