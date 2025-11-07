# [z7] konfiguracja serwera DNS `bind9`

1. zainstalowanie `bind9` i innych potrzebnych pakietów
2. edytowane pliki:
    * `/etc/bind/named.conf.local`
    * `/etc/bind/zones/db.prask.rocks`
3. sprawdzenie poprawności
    * `sudo named-checkconf` sprawdza poprawność konfiguracji bind9
    * `sudo named-checkzone prask.rocks /etc/bind/zones/db.prask.rocks` konfiguracji domeny
4. `sudo systemctl reload named`
5. `[localhost]$ dig @91.204.161.219 prask.rocks +short` zwraca `91.204.161.219` (samego siebie, bo tak ustawiłem)
6. ustawienie w panelu name.com, że nameserver to `91.204.161.219` i poczekanie na propagację
7. `[localhost]$ dig prask.rocks` zwraca to, co z `@91.204.161.219`
8. weryfikacja przez https://intodns.com/prask.rocks oraz https://zonemaster.net/en

### drugi serwer DNS

1. dodanie `allow-transfer { IP_DRUGIEGO_SERWERA; };` w `named.conf.local` dla strefy `prask.rocks`
2. konfiguracja u drugiej osoby:
```
zone "prask.rocks" {
    type slave;
    file "/var/cache/bind/db.prask.rocks";
    masters { 91.204.161.219; }; // primary IP
};
```
3. dodanie `ns2.prask.rocks` --> IP serwera drugiej osoby

czy koniecznie jest dodanie jakiś rekordów w pliku `db.prask.rocks` (dla `ns2.prask.rocks`)?


### Logi

1. skonfigurować logi w `/etc/bind/named.conf.local`
2. wydać polecenie `rndc querylog on` (jeśli chcemy logować zapytania od klientów)
3. `bind9` potrafi sam rotować logi, więc nie trzeba robić osobnego `logrotate`
