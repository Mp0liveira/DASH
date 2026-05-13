import requests
import time
import os

class ClienteDash:
    def __init__(self, urls_iniciais):
        """
        Inicializa o cliente DASH recebendo uma lista de URLs possíveis 
        para buscar o manifesto inicial em caso de falha.
        """
        self.urls_iniciais = urls_iniciais
        self.manifesto = None
        self.bandwidth_kbps = 0.0
        self.qualidade_escolhida = None
        self.servidor_ativo = None # Armazena a URL base do servidor em uso
        
    def baixar_manifesto(self):
        """
        Tenta baixar o manifesto iterando sobre a lista de URLs iniciais.
        Retorna o manifesto em JSON ou None se falhar em todas.
        """
        print("\n[1] Tentando baixar o manifesto...")
        
        for url_base in self.urls_iniciais:
            # Constrói o caminho completo para o manifesto
            url_manifesto = f"{url_base}/manifest"
            
            try:
                # Timeout de 3 segundos para não travar muito tempo se o server estiver offline
                response = requests.get(url_manifesto, timeout=3)
                
                if response.status_code == 200:
                    print(f"    Manifesto baixado com sucesso de: {url_base}")
                    self.manifesto = response.json()
                    
                    # Define o servidor ativo com base na lista de 'servers' do manifesto
                    # Pega o servidor com maior prioridade (menor número)
                    servidores = sorted(self.manifesto["servers"], key=lambda k: k['priority'])
                    self.servidor_ativo = servidores[0]['url']
                    
                    return self.manifesto
            except requests.RequestException:
                print(f"    Falha ao conectar em {url_base}. Tentando próximo...")

        print("    Erro crítico: Nenhum servidor inicial respondeu.")
        return None

    def medir_largura_de_banda(self, url_segmento_teste):
        """
        Baixa o segmento base para medir a rede e atualiza self.bandwidth_kbps.
        """
        print(f"\n[2] Iniciando teste de rede com: {url_segmento_teste}")
        
        try:
            inicio = time.perf_counter()
            response = requests.get(url_segmento_teste)
            final = time.perf_counter()

            tempo_download = final - inicio
            tamanho_bits = len(response.content) * 8

            # Cálculo de vazão em kbps
            self.bandwidth_kbps = (tamanho_bits / tempo_download) / 1000

            print(f"    Tempo de download: {tempo_download:.4f} s")
            print(f"    Tamanho do segmento: {tamanho_bits} bits")
            print(f"    Vazão calculada: {self.bandwidth_kbps:.2f} kbps")

        except requests.RequestException as e:
            print(f"    Erro ao medir banda: {e}")
            self.bandwidth_kbps = 0.0

        return self.bandwidth_kbps

    def selecionar_qualidade(self):
        """
        Aplica a Política 1 (Rate-Based) com margem de segurança de 20%.
        """
        print("\n[3] Selecionando a melhor qualidade (Política 1)...")
        
        if not self.manifesto:
            print("    Erro: Manifesto ausente.")
            return None

        representacoes = self.manifesto["representations"]
        
        # Define a pior qualidade como padrão (fallback seguro)
        self.qualidade_escolhida = representacoes[0]

        for rep in representacoes:
            # Fator de segurança: a vazão precisa ser 20% maior que o bitrate exigido
            # 1.2 * bitrate = 120% do bitrate
            vazao_exigida_com_folga = rep["bitrate_kbps"] * 1.2
            
            if self.bandwidth_kbps >= vazao_exigida_com_folga:
                self.qualidade_escolhida = rep
            else:
                break

        print(f"    Qualidade escolhida: {self.qualidade_escolhida['quality']} "
              f"(Requer {self.qualidade_escolhida['bitrate_kbps']} kbps | "
              f"Segurança 20%: {self.qualidade_escolhida['bitrate_kbps'] * 1.2:.2f} kbps)")
        return self.qualidade_escolhida
        
    def baixar_video(self, url_path):
        """
        Realiza o download montando a URL com o servidor ativo + url_path do JSON.
        """
        url_completa = f"{self.servidor_ativo}{url_path}"
        print(f"\n[4] Baixando o segmento: {url_completa}")
        
        try:
            response = requests.get(url_completa)

            folder_name = "output"
            file_name = f"{folder_name}/segmento_teste.mp4"

            if response.status_code == 200:
                os.makedirs(folder_name, exist_ok=True)
                with open(file_name, "wb") as f:
                    f.write(response.content)
                print(f"    Arquivo salvo como: {file_name}")
            else:
                print(f'    Erro ao baixar arquivo. Status: {response.status_code}')
        except requests.RequestException as e:
             print(f'    Falha de conexão durante o download: {e}')

    def executar(self):
        if not self.baixar_manifesto():
            return 

        # 2. Pega o url_path da pior representação e monta o link para o teste
        rep_teste = self.manifesto["representations"][0]
        url_teste = f"{self.servidor_ativo}{rep_teste['url_path']}"
        
        self.medir_largura_de_banda(url_teste)
        self.selecionar_qualidade()

        if self.qualidade_escolhida:
            self.baixar_video(self.qualidade_escolhida["url_path"])


if __name__ == '__main__':
    # Lista com as URLs para falha tolerante no startup
    urls_de_bootstrap = [
        "http://137.131.178.229:8080",
        "http://137.131.178.229:8081"
    ]
    
    cliente = ClienteDash(urls_de_bootstrap)
    cliente.executar()