from scapy.all import *
import time

# Lista 7 różnych typów odpowiedzi ICMP
responses = [
    {"type": 0, "code": 0, "name": "Echo Reply (Normal)"},
    {"type": 3, "code": 0, "name": "Net Unreachable"},
    {"type": 3, "code": 3, "name": "Port Unreachable"},
    {"type": 4, "code": 0, "name": "Source Quench (Slow down!)"},
    {"type": 5, "code": 0, "name": "Redirect (Wrong way)"},
    {"type": 11, "code": 0, "name": "Time Exceeded (TTL dead)"},
    {"type": 12, "code": 0, "name": "Parameter Problem"}
]

index = 0

def handle_icmp(packet):
    global index
    if packet.haslayer(ICMP) and packet[ICMP].type == 8: # Echo Request
        reply_info = responses[index % len(responses)]
        
        # Budowanie odpowiedzi
        ip_layer = IP(dst=packet[IP].src, src=packet[IP].dst)
        icmp_layer = ICMP(type=reply_info["type"], code=reply_info["code"], id=packet[ICMP].id)
        
        print(f"[+] Wysyłam: {reply_info['name']} do {packet[IP].src}")
        send(ip_layer/icmp_layer/packet[Raw].load if packet.haslayer(Raw) else ip_layer/icmp_layer, verbose=False)

def rotate_index():
    global index
    while True:
        time.sleep(1)
        index += 1
        print(f"[*] Zmiana trybu na: {responses[index % len(responses)]['name']}")

# Uruchomienie wątku zmieniającego tryb co sekundę
import threading
threading.Thread(target=rotate_index, daemon=True).start()

print("Status: Czekam na pingi... (Ctrl+C aby przerwać)")
sniff(filter="icmp", prn=handle_icmp)