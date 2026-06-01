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

echo "=== INICIANDO: A MORTE LENTA DA CONEXÃO ==="

sudo tc qdisc add dev ifb0 root tbf rate 2.5mbit burst 32kbit latency 400ms
echo "[00s] 2.5 Mbps (Excelente)"
sleep 8

sudo tc qdisc change dev ifb0 root tbf rate 1.2mbit burst 32kbit latency 400ms
echo "[08s] 1.2 Mbps (Ainda suporta 1080p ou 720p)"
sleep 6

sudo tc qdisc change dev ifb0 root tbf rate 800kbit burst 32kbit latency 400ms
echo "[14s] 800 kbps (A rede está degradando)"
sleep 6

sudo tc qdisc change dev ifb0 root tbf rate 400kbit burst 32kbit latency 400ms
echo "[20s] 400 kbps (Alerta vermelho)"
sleep 6

sudo tc qdisc change dev ifb0 root tbf rate 100kbit burst 32kbit latency 400ms
echo "[26s] 100 kbps (Gargalo absoluto - Stall iminente)"
sleep 15

sudo tc qdisc change dev ifb0 root tbf rate 2mbit burst 32kbit latency 400ms
echo "[41s] 2 Mbps (A conexão volta ao normal subitamente)"
sleep 10

echo "=== FIM DA SIMULAÇÃO ==="
sudo tc qdisc del dev $INTERFACE ingress
sudo tc qdisc del dev ifb0 root