#!/bin/bash

echo "Derrubando servidor na porta 8080"
sudo iptables -A OUTPUT -p tcp -d 137.131.178.229 --dport 8080 -j DROP
sleep 20

echo "Voltando 8080 e derrubando 8081"
sudo iptables -D OUTPUT -p tcp -d 137.131.178.229 --dport 8080 -j DROP
sleep 1
sudo iptables -A OUTPUT -p tcp -d 137.131.178.229 --dport 8081 -j DROP
sleep 20

echo "Limpando regras..."
sudo iptables -D OUTPUT -p tcp -d 137.131.178.229 --dport 8080 -j DROP