## 2

### a)

#### Instalacja Dockera

Instalacja Docker Engine wg instrukcji na stronie. Jeśli chcemy uruchamiać `docker` jako zwykły użytkownik to trzeba dodać się do grupy `docker` (i zalogować ponownie, by uzwględnić zmiany - opisane na Linux postinstall).

#### Tworzymy nową sieć dla kontenerów

* ` --subnet 10.0.0.0/24` określa podsieć tej sieci, kontenery będą dostawały adresy `10.0.0.1-253`
* `--gateway 10.0.0.254` określa bramę domyślną dla kontenerów w tej sieci
* `--driver bridge` - użyj sterownika mostka dla sieci. Kontenery mogą się dzięki temu mostkowi komunikować w tej sieci
* `prasknet` - nazwa sieci

```sh
docker network create --subnet 10.0.0.0/24 --gateway 10.0.0.254 --driver bridge prasknet --ipv6 --subnet 2a0b:5485:1:17::/64
```

Możemy zobaczyć sieci dockerowe za pomocą

```sh
docker network ls
```

#### Tworzymy katalogi dla kontenerów

```sh
mkdir -p /srv/www/{vm1,vm2}
```

#### Uruchamiamy kontenery

* `--net prasknet` uruchamia kontener w stworzonej wcześniej sieci
* `--ip X` nadaje kontenerowi stały adres IPv4 - chyba nie da się zmienić adresu działającego kontenera
* `--ip6 Y` nadaje kontenerowy stały adres IPv6
* `--cap-add=NET_ADMIN` daje kontenerowi linuxowe capability `NET_ADMIN` pozwalając mu na wprowadzanie zmian w konfiguracji sieci
* `--name vm1` daje przyjazną nazwę aby łatwo odnosić się do kontenera (zamiast hasha lub nazwy wygenerowanej losowo)
* `-d` uruchamia jako *detached*, czyli w tle
* `-v /srv/www/vm1:/usr/share/nginx/html:ro` zamontuj katalog `/srv/www/vm1` z hosta w `/usr/share/nginx/html` kontenera jako read-only. Dokonane zmiany są widoczne jedynie w kontenerze, nie może on modyfikować plików na host-cie.
* `nginx` to nazwa obrazu (image), który chcemy uruchomić w kontenerze

```sh
docker run --net prasknet --ip 10.0.0.1 --ip6 2a0b:5485:1:17::a --cap-add=NET_ADMIN --name vm1 -dv /srv/www/vm1:/usr/share/nginx/html:ro nginx
```

```sh
docker run --net prasknet --ip 10.0.0.2 --ip6 2a0b:5485:1:17::b --cap-add=NET_ADMIN --name vm2 -dv /srv/www/vm2:/usr/share/nginx/html:ro nginx
```

Aby sprawdzić, czy kontener działa w dobrej sieci, jego adres IP i maskę sieci:

```sh
docker inspect vm1 | grep -i networksettings -A 30
```

Adresy ustalam przy `docker run`, a maska `/24` jest właściwością sieci.

Listowanie uruchamianych kontenerów

```sh
docker ps
```

### b) Sieć L2

```sh
docker network ls
# prasknet pokazuje się na liście
```

### c) Adresacja IPv6 kontenerów

Zrobiona poprzez `--ipv6 --subnet 2a0b:5485:1:17::/64` w `docker network create` oraz `--ip6 <ipv6-tutaj>` w `docker run`.

### d) Regułka NAT

* `nft add table nat` dodaje nową tabelę nazwaną `nat` (jeśli jeszcze nie istnieje)
* `nft 'add chain nat postrouting { type nat hook postrouting priority 100 ; }'`
    * dodaje łańcuch o nazwie `postrouting` do tabeli `nat`
    * `{ type nat hook postrouting priority 100 ; }`
        * `type nat` - łańcuch operuje na NAT
        * `hook postrouting` - łańcuch operuje w *hooku* `postrouting` (po decyzji o routingu, zanim pakiet opuści hosta)
        * `priority 100` - prioritet względem innych łańcuchów, wyższa liczba wykonuje się później
* `nft add rule nat postrouting ip saddr 10.0.0.0/24 oif ens18 snat to 91.204.161.219`
    * dodaje regułę w tabeli `nat`, łańcuchu `postrouting`, który dopasowuje się do adresów w pakietach i wykonuje SNAT (Source NAT, czyli podmieniamy adres źródłowy)
        * `ip saddr 10.0.0.0/24` — dopasowuj pakiety z źródłowym IP w `10.0.0.0/24`.
        * `oif ens18` — dopasowuj do pakietów wychodzącyh przez interfejs `ens18`.
        * `snat to 91.204.161.219` — zamień adres źródłowy pakietu na `91.204.161.219`.
    * efekt: ruch z hostów/kontenerów w sieci `10.0.0.0/24`, który wychodzi przez interfejs `ens18` będzie wyglądał na zewnątrz jakby pochodził od `91.204.161.219`

```
nft add table nat \
&& nft 'add chain nat postrouting { type nat hook postrouting priority 100 ; }' \
&& nft add rule nat postrouting ip saddr 10.0.0.0/24 oif ens18 snat to 91.204.161.219
```

### e) Włączamy przekazywanie pakietów aka bycie routerem

```sh
echo 1 > /proc/sys/net/ipv4/ip_forward
```

### f) Adres bramy domyślnej

Jest ustawiony, bo uruchomiliśmy kontenery w sieci `prasknet`.

### g) Ustawiamy adresy interfejsowi związanemu z wirtualną siecią na głównej maszynie

Musimy znaleźć interfejs sieci prasknet:

```sh
ip l show type bridge
```

Szukamy interfejsu odpowiadającemu naszemu bridge (br-...) i nadajemy mu IPv4 `10.0.0.254/24`, IPv6 `fe80::1`

```sh
# u mnie sieć ma już IPv4, ale gdybyśmy musieli je ustawić:
# sudo ip addr add 10.0.0.254/24 dev br-3e3e47e9221c

sudo ip -6 addr add fe80::1/64 dev br-3e3e47e9221c

ip addr show dev br-3e3e47e9221c

sudo ip link set br-3e3e47e9221c up
```

## 3: Pingowanie nawzajem

#### Główna maszyna --> vm1, vm2

```sh
ping 10.0.0.1 -c 3
# ok
ping 10.0.0.2 -c 3
# ok
ping6 fe80::1%br-3e3e47e9221c -c 3
# ok
```

#### vm1, vm2 --> główna maszyna

jak to zrobić?

Umiem sprawdzić, że kontener ma dostęp do internetu:

```sh
docker exec -it vm1 /bin/bash
curl google.com
# dostaję odpowiedź
```

## 4: Konfiguracja nginx i load balancingu

Uruchomiłem obraz dockera `nginx`, więc wystarczy dodać `index.html` w `/srv/www/vm{1,2}/`. Następnie można już odpytywać z głównej maszyny:

```sh
$ curl 10.0.0.1
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document</title>
</head>
<body>
    Hi, this is vm1
</body>
</html>

$ curl 10.0.0.2
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document</title>
</head>
<body>
    Hi, this is vm2
</body>
</html>
```

Aby nasze vm1, vm2 były dostępne "z zewnątrz" ustawiam load balancing w głównym nginx-ie (w pliku `/etc/nginx/sites-enabled/prask`).
Jeśli któryś kontener będzie miał 2 faile w ciągu 2 sekund, nginx przestanie wysyłać do niego requesty na 2 sekundy, potem spróbuje ponownie.

```
upstream backend {
    server 10.0.0.1:80 max_fails=2 fail_timeout=2s;
    server 10.0.0.2:80 max_fails=2 fail_timeout=2s;
}

server {
    server_name proxy.prask.rocks;

    location / {
        proxy_pass http://backend;
    }

    listen 443 ssl; # managed by Certbot
    listen [::]:443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/proxy.prask.rocks/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/proxy.prask.rocks/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}
```

`# managed by Certbot`: aby mieć HTTPS poprosiłem o certyfikat od let's encrypt za pomocą certbota:
```sh
certbot --nginx -d proxy.prask.rocks
```