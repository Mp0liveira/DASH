#!/bin/bash

# ==========================================
# Configurações da Simulação
# ==========================================
INTERFACE="eth0"       # No WSL, é sempre eth0
TEMPO_SIMULACAO=40     # Tempo em segundos da limitação
BANDA_LIMITE="1000kbit" # Banda estrangulada do Servidor A
# ==========================================

echo "[*] Iniciando simulação de congestionamento na porta 8080 (DOWNLOAD)..."

# 1. Limpa regras antigas
sudo tc qdisc del dev $INTERFACE ingress 2>/dev/null
sudo tc qdisc del dev ifb0 root 2>/dev/null

# 2. Configura a interface virtual (IFB) para capturar o Download
sudo modprobe ifb numifbs=1
sudo ip link set dev ifb0 up

# 3. Desvia o tráfego de entrada (Ingress) da eth0 para a ifb0
sudo tc qdisc add dev $INTERFACE handle ffff: ingress
sudo tc filter add dev $INTERFACE parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev ifb0

# 4. Aplica o limite de banda na interface virtual
sudo tc qdisc add dev ifb0 root handle 1: htb default 10
sudo tc class add dev ifb0 parent 1: classid 1:1 htb rate $BANDA_LIMITE

# 5. O Pulo do Gato: Filtra APENAS o tráfego vindo da porta 8080 (Servidor A)
# sport = Source Port (Porta de Origem do pacote que está chegando)
sudo tc filter add dev ifb0 protocol ip parent 1: prio 1 u32 match ip sport 8080 0xffff flowid 1:1

echo "[!] Download da porta 8080 ESTRANGULADO para $BANDA_LIMITE."
echo "[-] A limitação será desfeita automaticamente em $TEMPO_SIMULACAO segundos..."
echo "    -> Wireshark pode capturar a queda de vazão agora!"

# 6. Aguarda o tempo da simulação
sleep $TEMPO_SIMULACAO

# 7. Desfaz tudo com segurança
echo ""
echo "[*] Tempo esgotado! Limpando as regras do Traffic Control..."
sudo tc qdisc del dev $INTERFACE ingress 2>/dev/null
sudo tc qdisc del dev ifb0 root 2>/dev/null

echo "[+] Limpeza concluída. A rede voltou ao normal."