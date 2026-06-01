#!/bin/bash
INTERFACE="wlp4s0"

echo "Limpando regras antigas..."
sudo tc qdisc del dev $INTERFACE ingress 2>/dev/null
sudo tc qdisc del dev ifb0 root 2>/dev/null

echo "Configurando interface virtual (IFB)..."
sudo modprobe ifb numifbs=1
sudo ip link set dev ifb0 up
sudo tc qdisc add dev $INTERFACE handle ffff: ingress
sudo tc filter add dev $INTERFACE parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev ifb0

echo "=== INICIANDO: OSCILAÇÃO FORTE (FORÇANDO STALL) ==="

sudo tc qdisc add dev ifb0 root tbf rate 1.5mbit burst 32kbit latency 400ms
echo "[00s] Fase 1: 1.5 Mbps (Construindo um pouco de buffer por 8s)"
sleep 8

sudo tc qdisc change dev ifb0 root tbf rate 50kbit burst 32kbit latency 400ms
echo "[08s] Fase 2: PANE NA REDE - 50 kbps! (O buffer vai secar agora)"
# Deixamos nessa velocidade péssima por 20 segundos para garantir o stall
sleep 20 

sudo tc qdisc change dev ifb0 root tbf rate 1.5mbit burst 32kbit latency 400ms
echo "[28s] Fase 3: Conexão restabelecida (1.5 Mbps)"
sleep 15

sudo tc qdisc change dev ifb0 root tbf rate 50kbit burst 32kbit latency 400ms
echo "[08s] Fase 4: PANE NA REDE - 50 kbps! (O buffer vai secar agora)"
# Deixamos nessa velocidade péssima por 20 segundos para garantir o stall
sleep 10

sudo tc qdisc change dev ifb0 root tbf rate 1.5mbit burst 32kbit latency 400ms
echo "[28s] Fase 5: Conexão restabelecida (1.5 Mbps)"
sleep 15

echo "=== FIM DA SIMULAÇÃO ==="
sudo tc qdisc del dev $INTERFACE ingress
sudo tc qdisc del dev ifb0 root