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

echo "=== INICIANDO: OSCILAÇÃO NORMAL (EFEITO PING-PONG) ==="

sudo tc qdisc add dev ifb0 root tbf rate 2mbit burst 32kbit latency 400ms
echo "[00s] Inicial: 2 Mbps (Espera-se 1080p)"
sleep 10

sudo tc qdisc change dev ifb0 root tbf rate 750kbit burst 32kbit latency 400ms
echo "[10s] Queda Leve: 750 kbps (Espera-se queda para 480p)"
sleep 6

sudo tc qdisc change dev ifb0 root tbf rate 1.5mbit burst 32kbit latency 400ms
echo "[16s] Subida Rápida: 1.5 Mbps (Espera-se subida para 720p/1080p)"
sleep 6

sudo tc qdisc change dev ifb0 root tbf rate 500kbit burst 32kbit latency 400ms
echo "[22s] Nova Queda: 500 kbps (Espera-se 360p)"
sleep 6

sudo tc qdisc change dev ifb0 root tbf rate 2mbit burst 32kbit latency 400ms
echo "[28s] Recuperação total: 2 Mbps"
sleep 10

echo "=== FIM DA SIMULAÇÃO ==="
sudo tc qdisc del dev $INTERFACE ingress
sudo tc qdisc del dev ifb0 root