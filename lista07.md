### przekazywanie pakietów

sprawdzamy, czy jest `1` (włączone):
```sh
cat /proc/sys/net/ipv4/ip_forward
```

### nftables

`nftables` działa w kernelu, ale jest usługa `nftables.service`, która odpowiada za ładowanie regułek do kernela.

U mnie usługa nie była aktywna:
```sh
systemctl status nftables
systemctl start nftables 
```

Plik konfiguracyjny `/etc/nftables.conf`.

Aktualne regułki można sprawdzić poprzez `nft list ruleset`.

Domyślna konfiguracja akceptuje wszystko:

```
#!/usr/sbin/nft -f

flush ruleset # zresetuj wszystkie istniejące regułki

# inet oznacza, że to wspólne dla ipv4 i v6
table inet filter {
        chain input {
                type filter hook input priority filter;
        }
        chain forward {
                type filter hook forward priority filter;
        }
        chain output {
                type filter hook output priority filter;
        }
}
```

W `nft list ruleset` widać sporo regułek ustawionych przez dockera, który niestety jeszcze jest na `iptables`. Jest wartswa kompatybilności między `iptables` a `nftables`, nazywa się `iptables-nft Ponadto są warningi, żeby nie ruszać tych automatycznie ustawionych regułek. 

Niestety nawet z `flush ruleset` na początku pliku `/etc/nftables.conf` docker dodaje swoje regułki. Efekt jest taki, że po reboocie one są dodane, ale po `systemctl reload nftables` już się nie pokazują.

TODO: jak to należy rozwiązać (usunąć dockerowe regułki? zostawić?)

## 1

[./lista07/z1_nftables.conf](./lista07/z1_nftables.conf)

## 2

Pełny config w [./lista07/z2_nftables.conf](./lista07/z2_nftables.conf)

oraz

```sh
systemctl reload nftables
```

Sprawdzenie: zakomentowanie `tcp dport {80,443} accept` i próba otwarcia strony `prask.rocks` w **nowej sesji incognito** nie uda się. Incognito jest ważne, żeby nawiązać *nowe* połączenie, a nie korzystać z potencjalnie istniejącego (i dziwić się, że nadal działa).

## 3

Przed konfiguracją próba połączenia (dla porównania):

```sh
ssh -p 222 ii339630@prask4 #prask4 to alias na ipv4 mojej vm w /etc/hosts
# timeout
```
Dodajemy regułki. Pełny config w [./lista07/z3_nftables.conf](./lista07/z3_nftables.conf)


Teraz pakiety docierają do vmki, ale ona je odrzuca - jest OK. 

```sh
$ ssh -p222 ii339630@prask4
ssh: connect to host prask4 port 222: Connection refused
```

## 4

Konfigurujemy regułki, żeby docker network `10.0.0.0/24` miał dostęp do internetu - [./lista07/z4_docker_internet.conf](./lista07/z4_docker_internet.conf)

```sh
docker run -it --rm --network prasknet --ip 10.0.0.42 alpine sh
(alpine) $ apk add wget
wget -4 google.com
# pobiera index.html z google.com
```

Sprawdzamy jakie są adresy `google.com` i `wolframalpha.com`:
```sh
host google.com
host wolframalpha.com
```

Dodajemy regułkę przekierowującą:
```
table ip my_nat {
    chain prerouting {
        # (...)

        # Google -> WolframAlpha
        ip daddr { 
            142.250.130.100,
             142.250.130.101,
             142.250.130.102,
             142.250.130.113,
             142.250.130.138,
             142.250.130.139 
        } tcp dport 80 dnat to 140.177.8.192

        # (...)
    }
}
```

Niestety google ma dużo adresów i na dodatek się zmieniają. Lepiej byłoby przechwytywać zapytania DNS o `google.com`, ale chyba nie da się tego zrobić tylko w `nftables`

## 5

> Wow! Umiem przewidywać przyszłe zadania!

Nie działa :(

> [!IMPORTANT]
> To nie działa przy DNS over HTTPS.

## 6 (icmp fun)

Wyłączamy obsługę ICMP w kernelu:

```sh
sysctl -w net.ipv4.icmp_echo_ignore_all=1
```

Uruchamiamy [skrypt w pythonie](./lista07/icmp_fun.py):
```sh
apt install libpcap-dev
python3 -m venv venv
source venv/bin/activate
pip install scapy
python3 icmp_fun.py
```

```sh
# Z lokalnego komputera:
ping prask4
```

## 7

## 8 (TTL)

```
table ip my_mangle {
    chain postrouting {
        type filter hook postrouting priority mangle; policy accept;

        # 1. Zwiększenie TTL dla wszystkich pakietów wychodzących interfejsem zewnętrznym
        oifname "ens18" ip ttl set 64
    }
}
```

## 9 dziwna zaawansowana regułka

```
table inet my_filter {
    chain forward {
        type filter hook forward priority 0; policy drop;
        
        ether saddr 00:ca:fe:ba:be:00 tcp dport 80 ip length != 50-1000 meta day 13 meta day Friday drop
    }
}
```