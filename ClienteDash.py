import requests
import time
from BufferManager import BufferManager

class ClienteDash:
    def __init__(self, urls_iniciais):
        self.urls_iniciais = urls_iniciais
        self.manifesto = None
        self.bandwidth_kbps = 0.0
        self.qualidade_escolhida = None
        self.servidor_ativo = None
        
        # Instanciando o nosso novo gerenciador de buffer
        self.buffer = BufferManager()

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

    def baixar_e_medir_segmento(self, url_path):
        """
        Baixa o segmento para a memória e retorna o tempo que levou e os bytes recebidos.
        Não salva no disco rígido.
        """
        url_completa = f"{self.servidor_ativo}{url_path}"
        
        try:
            inicio = time.time()
            response = requests.get(url_completa)
            final = time.time()

            if response.status_code == 200:
                tempo_download = final - inicio
                tamanho_bits = len(response.content) * 8
                return tempo_download, tamanho_bits
            
        except requests.RequestException as e:
            print(f"    [Erro de Rede] Falha ao baixar o segmento: {e}")
            
        return 0, 0

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

        duracao_segmento_s = self.manifesto.get("segment_duration_s", 2.0)
        
        # O player sempre começa no "escuro" (sem saber a banda). 
        # Forçamos a primeira qualidade a ser a mais baixa por segurança.
        self.qualidade_escolhida = self.manifesto["representations"][0]

        print("\n" + "="*50)
        print(" INICIANDO STREAMING (LOOP DE REPRODUÇÃO)")
        print("="*50)

        # Loop de download de cada segmento
        for i in range(1, num_segmentos_simulados + 1):
            print(f"\n--- Baixando Segmento {i} ---")
            print(f"    Pedindo qualidade: {self.qualidade_escolhida['quality']} ({self.qualidade_escolhida['bitrate_kbps']} kbps)")
            
            # 1. Faz o download do vídeo e anota o tempo
            tempo_download, tamanho_bits = self.baixar_e_medir_segmento(self.qualidade_escolhida["url_path"])
            
            if tempo_download > 0:
                # 2. Atualiza a banda calculada (em kbps)
                self.bandwidth_kbps = (tamanho_bits / tempo_download) / 1000
                print(f"    Download finalizado em {tempo_download:.2f}s | Vazão medida: {self.bandwidth_kbps:.2f} kbps")
                
                # 3. Atualiza o Buffer e vê se o vídeo travou
                can_play, stall = self.buffer.processar_download(tempo_download, duracao_segmento_s)
                
                # AQUI ENTRARIA O CÓDIGO PARA SALVAR NO CSV (Tarefa 1.2)
                # gerar_linha_csv(i, qualidade, vazao, buffer, can_play, stall...)
                
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
    # Roda a simulação para 10 segmentos de vídeo
    cliente.executar(num_segmentos_simulados=10)