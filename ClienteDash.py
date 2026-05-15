import requests
import datetime
import time
import csv
import os
from BufferManager import BufferManager

class ClienteDash:
    def __init__(self, urls_iniciais):
        self.urls_iniciais = urls_iniciais
        self.manifesto = None
        self.bandwidth_kbps = 0.0
        self.qualidade_escolhida = None
        self.servidor_ativo = None
        self.buffer = BufferManager()
        self.latencia_anterior_s = None
        self.jitter_ms = 0.0
        self.download_time_s = 0.0
        self.tamanho_segmento_bits = 0

    def baixar_manifesto(self):
        print("\n[*] Tentando baixar o manifesto...")
        for url_base in self.urls_iniciais:
            url_manifesto = f"{url_base}/manifest" if not url_base.endswith('/manifest') else url_base
            try:
                response = requests.get(url_manifesto, timeout=3)
                if response.status_code == 200:
                    self.manifesto = response.json()
                    servidores = sorted(self.manifesto["servers"], key=lambda k: k['priority'])
                    self.servidor_ativo = servidores[0]['url']
                    print(f"    Manifesto carregado. Servidor ativo: {self.servidor_ativo}")
                    return True
            except requests.RequestException:
                print(f"    Falha no servidor {url_base}. Tentando próximo...")
        print("    Erro: Nenhum servidor disponível.")
        return False
    
    def inicializar_csv(self, nome_arquivo="output/log_baseline.csv"):
        self.nome_arquivo_csv = nome_arquivo
        os.makedirs(os.path.dirname(self.nome_arquivo_csv) if os.path.dirname(self.nome_arquivo_csv) else '.', exist_ok=True)
        
        with open(self.nome_arquivo_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "segmento", 
                "timestamp",
                "server_id",
                "qualidade",
                "bitrate_kbps",
                "vazao_kbps",
                "download_time_s",
                "jitter_network_ms",
                "jitter_ewma_ms",
                "jitter_ms", # Campo temporário só pra apresentar a 1° entrega
                "buffer_level_s",
                "buffer_can_play",
                "rebuffer_event",
                "stall_duration_s",
                "failover_total"
            ])
            
    def registrar_csv(self, num_segmento, can_play, stall, timestamp_iso):        
        # O buffer_can_play é literalmente o inverso do indicador do rebuffering
        # Se ele pode tocar, é pq não houve rebuffering
        rebuffer_event = int(not can_play)
        
        with open(self.nome_arquivo_csv, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                num_segmento,
                timestamp_iso, # No momento não se aplica
                None, # No momento não se aplcia
                self.qualidade_escolhida["quality"],
                self.qualidade_escolhida["bitrate_kbps"],
                round(self.bandwidth_kbps, 2),
                round(self.download_time_s, 2),
                None, # No momento não se aplica
                None, # No momento não se aplica
                round(self.jitter_ms, 2),
                round(self.buffer.nivel_atual_s, 2),
                can_play,
                rebuffer_event,
                round(stall, 2),
                0 # No momento não se aplica (total de failover = 0)
            ])

    def baixar_e_medir_segmento(self, url_path):
        """
        Baixa o segmento para o buffer e retorna o tempo que levou e os bytes recebidos.
        """
        url_completa = f"{self.servidor_ativo}{url_path}"
        
        try:
            inicio = time.time()
            response = requests.get(url_completa)
            final = time.time()

            if response.status_code == 200:
                self.download_time_s = final - inicio
                self.tamanho_segmento_bits = len(response.content) * 8

                # A função extrai o TTFB, que é o time to first byte
                # É quanto tempo demora desde a requisição até o recebimento do 1° byte do pacte
                latencia_atual_s = response.elapsed.total_seconds()

                if self.latencia_anterior_s is not None:
                    # Jitter é a diferença de tempo entre cada pactore
                    variacao_s = abs(latencia_atual_s - self.latencia_anterior_s)
                    self.jitter_ms = variacao_s * 1000
                else:
                    self.jitter_ms = 0.0 # Seria o caso do 1° pacote, não tem jitter pq não tem com o que comparar

                self.latencia_anterior_s = latencia_atual_s

                return True

        except requests.RequestException as e:
            print(f"    [Erro de Rede] Falha ao baixar o segmento: {e}")
            
        return False

    def selecionar_qualidade(self):
        """ Política 1 (Rate-Based) com 20% de margem de segurança """
        representacoes = self.manifesto["representations"]
        self.qualidade_escolhida = representacoes[0] # Fallback (pior qualidade)

        for rep in representacoes:
            vazao_exigida_com_folga = rep["bitrate_kbps"] * 1.2
            if self.bandwidth_kbps >= vazao_exigida_com_folga:
                self.qualidade_escolhida = rep
            else:
                break

    def executar(self, num_segmentos_simulados=10):
        """
        Loop principal do player. Fica rodando e baixando os próximos segmentos.
        """
        if not self.baixar_manifesto():
            return

        self.inicializar_csv("output/log_baseline.csv")
        duracao_segmento_s = self.manifesto.get("segment_duration_s")
 
        # Forçamos a primeira qualidade a ser a mais baixa por segurança.
        self.qualidade_escolhida = self.manifesto["representations"][0]

        print("\n" + "="*50)
        print(" INICIANDO STREAMING")
        print("="*50)

        # Loop de download de cada segmento
        for i in range(1, num_segmentos_simulados + 1):
            print(f"\n--- Baixando Segmento {i} ---")
            print(f"    Pedindo qualidade: {self.qualidade_escolhida['quality']} ({self.qualidade_escolhida['bitrate_kbps']} kbps)")
            
            # 1. Faz o download do vídeo e anota o tempo
            sucesso = self.baixar_e_medir_segmento(self.qualidade_escolhida["url_path"])
            timestamp_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

            if sucesso:
                # 2. Atualiza a banda calculada (em kbps)
                self.bandwidth_kbps = (self.tamanho_segmento_bits / self.download_time_s) / 1000
                print(f"    Download finalizado em {self.download_time_s:.2f}s | Vazão medida: {self.bandwidth_kbps:.2f} kbps")
                
                # 3. Atualiza o Buffer e vê se o vídeo travou
                can_play, stall = self.buffer.processar_download(self.download_time_s, duracao_segmento_s)
                
                # CSV
                self.registrar_csv(i, can_play, stall, timestamp_iso)
                
                # 4. Com a nova banda medida, recalcula a qualidade para o PRÓXIMO loop
                self.selecionar_qualidade()
            else:
                print("    Falha crítica ao baixar segmento. Interrompendo streaming.")
                break


if __name__ == '__main__':
    urls_de_bootstrap = [
        "http://137.131.178.229:8080",
        "http://137.131.178.229:8081"
    ]
    
    cliente = ClienteDash(urls_de_bootstrap)
    cliente.executar(num_segmentos_simulados=20)