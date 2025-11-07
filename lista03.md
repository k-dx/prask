### konfiguracja ipv6

`ip addr` zgłasza jedynie link-local ipv6: `inet6 fe80::1b55:144d:d7e3:a638/64 scope link`
Ponadto nie ma domyślnej trasy dla ipv6:
```
ip -6 route show
```

#### Można je dodać tymczasowo:

```
# adres maszyny to będzie ::2
sudo ip -6 addr add 2a0b:5485:1:17::2/64 dev ens18
# domyślna trasa ustawiona na ipv6 gateway
sudo ip -6 route add default via 2a0b:5485:1:17::1 dev ens18
```

#### Lub permanentnie w `/etc/network/interfaces`:

```
iface ens18 inet6 static
    address 2a0b:5485:1:17::2
    netmask 64
    gateway 2a0b:5485:1:17::1
```

Potem restart sieci żeby uwzględnić zmiany:
```
sudo ifdown ens18 || true && sudo ifup ens18
```

#### IPv6 health check

Trzeba wpisać adres(y) ipv6 DNS-ów u dostawcy domeny aby dostać zaliczyć ostatni test "IPv6 nameserver delegation and glue trace"

