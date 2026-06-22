#!/bin/bash

# ==========================================
# Configurações da Simulação de Failover
# ==========================================
IP_SERVIDOR="137.131.178.229"
PORTA_PRIMARIA="8080"
TEMPO_QUEDA=20
# ==========================================

echo "[*] Iniciando simulação de QUEDA do Servidor A (porta $PORTA_PRIMARIA)..."

# 1. Garante que não há regras antigas
sudo iptables -D OUTPUT -p tcp -d $IP_SERVIDOR --dport $PORTA_PRIMARIA -j DROP 2>/dev/null

# 2. Insere a regra de bloqueio: Descarta (DROP) qualquer pacote indo para o Servidor A
# Isso simula um cabo rompido ou servidor travado, ativando o timeout de 2s do seu Python
sudo iptables -I OUTPUT -p tcp -d $IP_SERVIDOR --dport $PORTA_PRIMARIA -j DROP

echo "[!] Servidor A inacessível (Pacotes DROPADOS)."
echo "[!] O Player vai registrar o timeout e iniciar o failover para o Servidor B."
echo "[-] A conexão será restaurada em $TEMPO_QUEDA segundos..."

# 3. Trava o script e aguarda
sleep $TEMPO_QUEDA

# 4. Desfaz o bloqueio
echo ""
echo "[*] Tempo esgotado! Restaurando a rota para o Servidor A..."
sudo iptables -D OUTPUT -p tcp -d $IP_SERVIDOR --dport $PORTA_PRIMARIA -j DROP

echo "[+] Limpeza concluída. O Servidor A está online novamente."