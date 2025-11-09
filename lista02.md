
# Lista 02

## nginx

```
apt update && apt install nginx
```

automatycznie uruchamia serwer z domyślną stroną powitalną

Istotne pliki:
* `/etc/nginx/sites-available/*` - konfiguracja stron możliwych do włączenia, jest `default` na którym się wzorowałem
* `/etc/nginx/sites-enabled/*` - katalog z linkami symbolicznymi do `sites-available`, które są włączone
* `/var/www/*` - katalog z zawartościami stron (HTML)

## 1b) certyfikat self-signed:

```
openssl req -x509 -newkey rsa:2048 -keyout www1.prask.rocks.key.pem -out www1.prask.rocks.cert.pem -days 365 -noenc -subj "/CN=www1.prask.rocks"
```

Taki certyfikat nie jest dobry z punktu widzenia klienta, bo nie jest on w stanie zweryfikować, czy pochodzi z zaufanego źródła - każdy może sobie taki wygenerować. Brakuje zaufanego (przez klienta) CA, który by potwierdził że to jest uczciwie mój certyfikat.

Wygenerowany certyfikat wrzuciłem do `/etc/ssl/certs/`, a klucz prywatny do `/etc/ssl/private`.

## własne CA

1c) generujemy klucz prywatny (do zarządzania CA):
```sh
openssl genpkey -algorithm RSA -out ca.key.pem -aes256 -pkeyopt rsa_keygen_bits:2048
```

1c) generujemy self-signed CA certificate:
```sh
openssl req -x509 -new -noenc -key ca.key.pem -sha256 -days 365 -out ca.cert.pem -subj "/CN=PraskRocksCA" -config <(cat <<-EOF
[ req ] # konfiguracja dla polecenia req
x509_extensions = ca_extensions

[ ca_extensions ] # rozszerzenia dla certyfikatu CA, nazwa dowolna
basicConstraints = critical, CA:TRUE
keyUsage = critical, digitalSignature, cRLSign, keyCertSign
EOF
)
```

sprawdzamy czy typ certyfikatu to CA:
```sh
openssl x509 -in ca.cert.pem -noout -text
```

Dostajemy:
```
		(...)
		X509v3 extensions:
			X509v3 Basic Constraints: critical
				CA:TRUE
			X509v3 Key Usage: critical
				Digital Signature, Certificate Sign, CRL Sign
		(...)
```


Zapisujemy konfigurację rozszerzeń do pliku `extensions.cnf`:
```sh
cat <<-EOF > extensions.www2.cnf
[ req ]
distinguished_name = req_distinguished_name
req_extensions = csr_extensions
prompt = no

[ req_distinguished_name ]
CN = www2.prask.rocks

[ csr_extensions ]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
basicConstraints = critical, CA:FALSE
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = www2.prask.rocks
EOF
```

`alt_names` to SAN (Subject ALternative Name). Bez tego Firefox nie akceptuje certyfikatu.

1d) generujemy CSR (certificate signing request) dla domeny `www2.prask.rocks`:
```sh
openssl req -new -noenc -newkey rsa:2048 -keyout www2.prask.rocks.key.pem -out www2.prask.rocks.csr.pem -config extensions.www2.cnf
```

sprawdzamy czy typ CSR to serwer:
```sh
openssl req -in www2.prask.rocks.csr.pem -noout -text
```

Dostajemy:
```
		(...)
        Attributes:
            Requested Extensions:
                X509v3 Key Usage: critical
                    Digital Signature, Key Encipherment
                X509v3 Extended Key Usage: 
                    TLS Web Server Authentication, TLS Web Client Authentication
                X509v3 Basic Constraints: critical
                    CA:FALSE
		(...)
```


1d) podpisujemy CSR jako CA:

```sh
openssl x509 -req -in www2.prask.rocks.csr.pem -CA ca.cert.pem -CAkey ca.key.pem -CAcreateserial -out www2.prask.rocks.cert.pem -days 365 -sha256 -extensions csr_extensions -extfile extensions.www2.cnf
```

#### Konfiguracja certyfikatów w nginx

Nginx domyślnie dopuszcza TLSv1.2 i v1.3, więc nie trzeba tego dodatkowo konfigurować.

```
server {
    ...

    ssl_certificate  /path/to/cert.pem
    ssl_certificate_key /path/to/private_key.pem
}
```

### Instalacja certyfikatu CA w komputerze (Ubuntu)

Teraz możemy zainstalować sobie w komputerze certyfikat CA. Oznacza to, że mu ufamy i nasza strona powinna działać po HTTPS.

```
# rsync-iem skopiowalem certyfikat z vm na komputer
sudo cp ca.cert.pem /usr/local/share/ca-certificates/my-ca.crt
sudo update-ca-certificates
```

[Firefox nie używa systemowych certyfikatów](https://askubuntu.com/questions/1315866/how-to-make-firefox-trust-my-companies-certificate-on-my-machine)

### 1e) Certyfikat z wildcardem

Generujemy CSR z wildcardem:

```sh
openssl req -new -noenc -newkey rsa:2048 -keyout wildcard.rocks.key.pem -out wildcard.rocks.csr.pem -config <(cat <<-EOF
[ req ]
distinguished_name = req_distinguished_name
req_extensions = csr_extensions
prompt = no

[ req_distinguished_name ]
CN = *.rocks

[ csr_extensions ]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
basicConstraints = critical, CA:FALSE
EOF
)
```

Podpisujemy CSR jako CA:

```sh
openssl x509 -req -in wildcard.rocks.csr.pem -CA ca.cert.pem -CAkey ca.key.pem -CAcreateserial -out wildcard.rocks.cert.pem -days 365 -sha256
```


### 1f) Let's encrypt

instalujemy certbota, który będzie automatycznie odnawiał certyfikat
```sh
sudo apt update && sudo apt install certbot python3-certbot-nginx -y
```

następnie prosimy go o certyfikat dla `prask.rocks` i `www.prask.rocks`
```sh
sudo certbot --nginx -d prask.rocks -d www.prask.rocks
```

certbot zapisuje go w `/etc/letsencrypt/live/prask.rocks` i automatycznie modyfikuje konfigurację nginx


### Rezultat w przeglądarce

* www1: krzyczy, że self-signed i nie akceptuje certyfikatu
* www2: krzyczy, że self-signed i nie akceptuje certyfikatu
    * po dodaniu certyfikatu CA w firefoxie powinno być ok, ale nie działa :(
* www3: ?
* www: przeglądarka ufa let's encrypt, więc jest OK

## Zad 2

https://www.ssllabs.com/ssltest/analyze.html pokazuje wynik A dla `prask.rocks` ;)

* HSTS - HTTP Strict Transport Security to mechanizm instruujący przeglądarki żeby zawsze komunikowały się ze stroną poprzez HTTPS, nigdy HTTP. Strona może wysyłać nagłówek HSTS (`Strict-Transport-Security`) w odpowiedzi HTTPS. Przeglądarka wtedy też blokuje obejście błędów certyfikatów przez użytkownika.
* PFS (FS) - (Perfect) Forward Secrecy. Mechanizm kryptograficzny, który zapewnia, że kompromitacja (ujawnienie) kluczy prywatnych nie spowoduje ujawnienia przeszłych bądź przyszłych szyfrowanych komunikacji. Działa na zasadzie generowanie świeżych kluczy do każdej sesji komunikacji. Ważne, bo chroni przed atakami typu "record now, decrypt later".
* ALPN - Application-Layer Protocol Negotation to rozszerzenie TLS, które pozwala klientowi i serwerowi uzgodnić jaki protokół warstwy aplikacji będzie używany już podczas TLS handshake (zamiast później, co wymaga wysyłania dodatkowych wiadomości)
* NPN - Next Protocol Negotiation to przestarzałe rozszerzenie TLS stworzone przez GOogle w ramach rozwijania protokołu SPDY. Przekształciło się w ALPN
* CAA - Certificate Authority Authorization to mechanizm DNS pozwalający właścicielowi domeny wyznaczyć, które Certificate Authority (CA) mogą wystawiać certyfikaty SSL/TLS dla domeny
    * realizowane poprzez specjalny rekord DNS typu CAA
    * czy to działa tak, że klient (przeglądarka) odpytuje serwer DNS o rekord CAA, jeśli ten się nie zgadza z CA które wydało certyfikat to ostrzega użytkownika? Jaki ma to sens jeśli zapytania DNS są nieszyfrowane?
* OCSP - Online Certificate Status Protocol to protokół używany do sprawdzania statusu odwołania certyfikatów X.509.
    
## Zad 3

Dodajemy nagłówki poprzez konfigurację nginx-a:
```
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
add_header Content-Security-Policy "default-src 'self' https://ipv6.he.net/certification/create_badge.php?pass_name=kdx&badge=1;";
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header Referrer-Policy "strict-origin";
add_header Permissions-Policy "geolocation=(); midi=(); notifications=(); push=(); sync-xhr=(); accelerometer=(); gyroscope=(); magnetometer=(); payment=(); usb=(); vr=(); camera=(); microphone=(); speaker=(); vibrate=(); ambient-light-sensor=(); autoplay=(); encrypted-media=(); execute-clipboard=(); document-domain=(); fullscreen=(); imagecapture=(); lazyload=(); legacy-image-formats=(); oversized-images=(); unoptimized-lossy-images=(); unoptimized-lossless-images=(); unsized-media=(); vertical-scroll=(); web-share=(); xr-spatial-tracking=();";
```

`Content-Security-Policy` wymagało wrzucenia CSS do osobnego pliku (bo nie chce mi się liczyć hasha z tego CSS by używać go w nagłówku).

## Zad 4

HSTS skonfigurowałem już w poprzednim zadaniu dodając nagłówek `Strict-Transport-Security`.

CAA konfigurujemy w DNS (bind9), dodając następujące rekordy:
```
; CAA records to allow Let's Encrypt to issue certificates
@       IN      CAA     0 issue "letsencrypt.org"
www     IN      CAA     0 issue "letsencrypt.org"
@       IN      CAA     0 issuewild "letsencrypt.org"
www     IN      CAA     0 issuewild "letsencrypt.org"
```

Dzięki temu na ssllabs.com dostaję grade A+.

---

# Konfiguracja nginx

```
# --- www1 -------------------------------------------------------------------

server {
	listen 80;
	listen [::]:80;

	server_name www1.prask.rocks;

	return 301 https://$host$request_uri;

}

server {
	listen 443 ssl;
	listen [::]:443 ssl;

	server_name www1.prask.rocks;

	ssl_certificate /etc/ssl/certs/www1.prask.rocks.cert.pem;
	ssl_certificate_key /etc/ssl/private/www1.prask.rocks.key.pem;

	root /var/www/prask.rocks;
	index index.html;

	location / {
		try_files $uri $uri/ =404;
	}
}

# --- www2 -------------------------------------------------------------------

server {
	listen 80;
	listen [::]:80;

	server_name www2.prask.rocks;

	return 301 https://$host$request_uri;

}

server {
	listen 443 ssl;
	listen [::]:443 ssl;

	server_name www2.prask.rocks;

	ssl_certificate /etc/ssl/certs/www2.prask.rocks.cert.pem;
	ssl_certificate_key /etc/ssl/private/www2.prask.rocks.key.pem;

	root /var/www/prask.rocks;
	index index.html;

	location / {
		try_files $uri $uri/ =404;
	}
}

# -------------------------------------------------------------

server {
	server_name prask.rocks;

	root /var/www/prask.rocks;
	index index.html;

	location / {
		try_files $uri $uri/ =404;
	}

    listen 443 ssl; # managed by Certbot
    listen [::]:443 ssl ipv6only=on; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/prask.rocks/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/prask.rocks/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

	include /etc/nginx/snippets/security-headers.conf;
}
server {
    server_name www.prask.rocks; # managed by Certbot

	root /var/www/prask.rocks;
	index index.html;

	location / {
		try_files $uri $uri/ =404;
	}

    listen 443 ssl; # managed by Certbot
    listen [::]:443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/prask.rocks/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/prask.rocks/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

	include /etc/nginx/snippets/security-headers.conf;
}

server {
    if ($host = prask.rocks) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


	listen 80;
	listen [::]:80;

	server_name prask.rocks;
    return 404; # managed by Certbot


}
server {
    if ($host = www.prask.rocks) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    listen 80 ;
    listen [::]:80 ;
    server_name www.prask.rocks;
    return 404; # managed by Certbot
}

```
