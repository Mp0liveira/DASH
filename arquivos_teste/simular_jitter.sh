#!/bin/bash

# ==========================================
# Configurações da Simulação de Jitter
# ==========================================
INTERFACE="eth0"
TEMPO_SIMULACAO=40
# ==========================================

echo "[*] Iniciando simulação de JITTER (Instabilidade) na porta 8080..."

# 1. Limpa regras antigas
sudo tc qdisc del dev $INTERFACE ingress 2>/dev/null
sudo tc qdisc del dev ifb0 root 2>/dev/null

# 2. Configura a interface virtual (IFB) para capturar o Download
sudo modprobe ifb numifbs=1
sudo ip link set dev ifb0 up
sudo tc qdisc add dev $INTERFACE handle ffff: ingress
sudo tc filter add dev $INTERFACE parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev ifb0

# 3. Cria a árvore principal (Com banda folgada de 5000kbit)
sudo tc qdisc add dev ifb0 root handle 1: htb default 10
sudo tc class add dev ifb0 parent 1: classid 1:1 htb rate 5000kbit

# 4. O Pulo do Gato (NetEm): Injeta um atraso base de 100ms, variando +- 80ms aleatoriamente
sudo tc qdisc add dev ifb0 parent 1:1 handle 20: netem delay 100ms 80ms 25% distribution normal

# 5. Filtra o tráfego da porta 8080 para passar por esse caos
sudo tc filter add dev ifb0 protocol ip parent 1: prio 1 u32 match ip sport 8080 0xffff flowid 1:1

echo "[!] Tráfego da porta 8080 agora está altamente INSTÁVEL (Jitter Injetado)."
echo "[-] A banda nominal continua alta, mas a entrega está caótica."
echo "[-] A simulação será desfeita em $TEMPO_SIMULACAO segundos..."

# 6. Aguarda o tempo da simulação
sleep $TEMPO_SIMULACAO

# 7. Desfaz tudo
echo ""
echo "[*] Tempo esgotado! Limpando as regras do NetEm..."
sudo tc qdisc del dev $INTERFACE ingress 2>/dev/null
sudo tc qdisc del dev ifb0 root 2>/dev/null

echo "[+] Limpeza concluída. A rede voltou a ser estável."