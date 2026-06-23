# Para rodar: python3 ClienteDash <nome_da_saida> <algoritmo> <margem>
#
# <nome_da_saida> pode assumir qualquer valor (pasta do output)
# <algoritmo> = rate_based/bba0/bba2/heuristica
# <margem> é qualquer valor númerico para a margem de segurança do rate_based e heuristica
# Por padrão, caso não seja passado nenhum parâmetro, a saída será salva na pasta output/padrão no rate_based sem margem
# de segurança (margem = 1)
#
# A pasta arquivos_teste contém alguns scripts bash usados para simular ambientes de rede
# Caso queira testar, basta rodar o código em um terminal e rodar o script escolhido em um outro terminal simultâneamente

import json
import requests
import datetime
import time
import csv
import sys
import os
from BufferManager import BufferManager
from GeradorGraficos import GeradorGraficos


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
        self.fase_arranque_ativa = True
        self.total_failovers = 0
        self.servidores_ordenados = []
        self.jitter_ewma_ms = 0.0


    def baixar_manifesto(self):
        print("\n[*] Tentando baixar o manifesto...")
        for url_base in self.urls_iniciais:
            url_manifesto = f"{url_base}/manifest" if not url_base.endswith('/manifest') else url_base
            try:
                response = requests.get(url_manifesto, timeout=3)
                if response.status_code == 200:
                    self.manifesto = response.json()
                    
                    # === INÍCIO DO PRINT DO MANIFESTO ===
                    print("\n--- Conteúdo do Manifesto ---")
                    # O indent=4 deixa o JSON formatado com quebras de linha e espaçamentos
                    print(json.dumps(self.manifesto, indent=4, ensure_ascii=False))
                    print("-----------------------------\n")
                    # === FIM DO PRINT DO MANIFESTO ===
                    
                    self.servidores_ordenados = sorted(self.manifesto["servers"], key=lambda k: k['priority'])
                    self.servidor_ativo = self.servidores_ordenados[0]
                    print(f"    Manifesto carregado. Servidor ativo: {self.servidor_ativo['url']}")
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
                "buffer_level_s",
                "buffer_can_play",
                "rebuffer_event",
                "stall_duration_s",
                "failover_total"
            ])


    def registrar_csv(self, num_segmento, buffer_can_play, stall, timestamp_iso):        
            # Se houve tempo de stall (travamento), então houve um evento de rebuffering
            rebuffer_event = 1 if stall > 0 else 0
            
            with open(self.nome_arquivo_csv, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    num_segmento,
                    timestamp_iso,
                    self.servidor_ativo["id"], # server_id
                    self.qualidade_escolhida["quality"],
                    self.qualidade_escolhida["bitrate_kbps"],
                    round(self.bandwidth_kbps, 2), # Vazão medida
                    round(self.download_time_s, 2),
                    round(self.jitter_ms, 2), # jitter_network_ms
                    round(self.jitter_ewma_ms, 2), # jitter_ewma_ms (agora exportando a média móvel correta)
                    round(self.buffer.nivel_atual_s, 2), # Nível do buffer
                    buffer_can_play, # 1 se rodou liso, 0 se travou
                    rebuffer_event,  # 1 se travou, 0 se rodou liso
                    round(stall, 2),
                    self.total_failovers,
                ])

    def baixar_com_failover(self, url_path):
        """
        Tenta baixar o segmento. Se falhar, busca um servidor alternativo via /health
        """
        url_completa = f"{self.servidor_ativo['url']}{url_path}"
        
        try:
            # Pedido normal (adicionado stream=True)
            response = requests.get(url_completa, timeout=2, stream=True)
            response.raise_for_status()
            return response
            
        except requests.RequestException as e:
            print(f"    [!] Servidor ativo ({self.servidor_ativo['url']}) caiu ou deu timeout!")
            print("    [*] Iniciando procedimento de FAILOVER...")
            
            inicio_failover = time.time()
            for servidor in self.servidores_ordenados:
                url_candidata = servidor['url']
                
                if url_candidata == self.servidor_ativo['url']:
                    continue
                    
                print(f"    [*] Testando Health Check em: {url_candidata}/health")
                try:
                    health_resp = requests.get(f"{url_candidata}/health", timeout=2)
                    
                    if health_resp.status_code == 200:
                        print(f"    [+] Servidor {url_candidata} está VIVO! Migrando...")
                        self.servidor_ativo = servidor
                        self.total_failovers += 1
                        
                        nova_url = f"{self.servidor_ativo['url']}{url_path}"
                        final_failover = time.time()
                        tempo_failover = final_failover - inicio_failover
                        print(f"    [!] Tempo para ocorrer o failover: {tempo_failover:.2f}s")
                        
                        # Retornando a nova URL com stream=True
                        return requests.get(nova_url, timeout=3, stream=True)
                        
                except requests.RequestException:
                    print(f"    [-] Servidor {url_candidata} também está morto.")
            
            print("    [!] ERRO FATAL: Todos os servidores estão indisponíveis.")
            raise Exception("Apagão de Rede")
        

    def baixar_e_medir_segmento(self, url_path):
        """
        Baixa o segmento e mede o jitter entre os pacotes (chunks) internos.
        """
        inicio = time.time()
        
        while True:
            try:
                response = self.baixar_com_failover(url_path)

                if response.status_code == 200:
                    tamanho_total_bytes = 0
                    latencia_anterior_chunk_s = None
                    soma_jitter_chunks_s = 0.0
                    num_chunks_medidos = 0

                    tempo_ultimo_chunk = time.time()

                    # O download real ocorre aqui. Se a conexão cair, vai gerar um ReadTimeout!
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            agora = time.time()
                            tamanho_total_bytes += len(chunk)
                            
                            latencia_chunk_s = agora - tempo_ultimo_chunk
                            
                            if latencia_anterior_chunk_s is not None:
                                variacao_s = abs(latencia_chunk_s - latencia_anterior_chunk_s)
                                soma_jitter_chunks_s += variacao_s
                                num_chunks_medidos += 1
                                
                            latencia_anterior_chunk_s = latencia_chunk_s
                            tempo_ultimo_chunk = agora

                    final = time.time()
                    
                    self.download_time_s = final - inicio
                    self.tamanho_segmento_bits = tamanho_total_bytes * 8

                    if num_chunks_medidos > 0:
                        self.jitter_ms = (soma_jitter_chunks_s / num_chunks_medidos) * 1000
                    else:
                        self.jitter_ms = 0.0 

                    alpha = 0.125
                    if self.jitter_ewma_ms == 0.0:
                        self.jitter_ewma_ms = self.jitter_ms 
                    else:
                        self.jitter_ewma_ms = (alpha * self.jitter_ms) + ((1 - alpha) * self.jitter_ewma_ms)

                    # Se chegou até aqui, o download foi um sucesso. Saímos da função.
                    return True

            except Exception as e:
                print(f"    [!] Conexão interrompida durante a leitura dos pacotes: {e}")
                print("    [*] Repetindo tentativa do segmento para acionar failover...")
                # Fica preso no while até conseguir baixar o segmento de algum dos servidores


    def selecionar_qualidade_rate_based(self, margem_seguranca):
        """ Política 1 (Rate-Based) com 20% de margem de segurança """
        representacoes = self.manifesto["representations"]
        self.qualidade_escolhida = representacoes[0] # Fallback (pior qualidade)

        for rep in representacoes:
            vazao_exigida_com_folga = rep["bitrate_kbps"] * margem_seguranca
            if self.bandwidth_kbps >= vazao_exigida_com_folga:
                self.qualidade_escolhida = rep
            else:
                break


    def selecionar_qualidade_buffer_based(self):
        """ Política 2 (Buffer-Based) com Histerese (Anti Ping-Pong) e Teto de Banda """
        representacoes = sorted(self.manifesto["representations"], key=lambda k: k['bitrate_kbps'])
        nivel_buffer = self.buffer.nivel_atual_s
        
        BUFFER_MIN = 10.0 
        BUFFER_MAX = 30.0 
        
        # 1. Calcula o índice ideal matematicamente
        if nivel_buffer <= BUFFER_MIN:
            novo_indice = 0
        elif nivel_buffer >= BUFFER_MAX:
            novo_indice = len(representacoes) - 1
        else:
            progresso = (nivel_buffer - BUFFER_MIN) / (BUFFER_MAX - BUFFER_MIN)
            novo_indice = round(progresso * (len(representacoes) - 1))
            
        # 2. Histerese (trava de queda)
        # Só aplicamos a trava se o player já estava tocando alguma coisa antes
        if self.qualidade_escolhida is not None:
            # Descobre qual é o índice da qualidade que estava tocando no segmento anterior
            indice_atual = representacoes.index(self.qualidade_escolhida)
            
            # Se o cálculo escolhe um segmento de pior qualidade, comparamos
            if novo_indice < indice_atual:
                # O buffer ainda está numa zona super confortável? (nosso caso, olhamos se >= 80%)
                # Se sim, mantemos a qualidade, mesmo que o cálculo tenha mandado abaixar
                if nivel_buffer > (BUFFER_MAX * 0.8):
                    novo_indice = indice_atual

        # 3. Teto de Banda
        # Quando implementamos o BBA0/BBA2, surgiu um novo problema de oscilação entre as duas melhoers qualidade
        # O código abaixo faz com que o player prefira a estabilidade (na 2° melhor qualidade) do que a oscilação

        # Multiplicamos a banda medida para permitir uma leve folga (já que temos buffer para queimar)
        limite_banda = self.bandwidth_kbps * 1.8
        
        # Se o buffer pediu uma qualidade que é muito maior que a capacidade da rede, nós cortamos
        while novo_indice > 0 and representacoes[novo_indice]['bitrate_kbps'] > limite_banda:
            novo_indice -= 1

        # 4. Aplica a decisão final
        self.qualidade_escolhida = representacoes[novo_indice]


    def selecionar_qualidade_heuristica_jitter(self, margem_seguranca):
        """ Política 3: evolução da Política 2 (Buffer-Based) com penalidade por Jitter EWMA.
        Mesma estrutura de fases da BBA2 (arranque por vazão, depois por buffer), mas o
        jitter penaliza a vazão usada tanto no arranque quanto no teto de banda da fase de buffer,
        em vez de decidir só pela vazão (o que causava ping-pong, igual o baseline)."""
        representacoes = sorted(self.manifesto["representations"], key=lambda k: k['bitrate_kbps'])

        # Heurística: penalizamos a vazão medida proporcionalmente ao Jitter EWMA
        # Define-se que 500ms de Jitter EWMA representam o cenário crítico (100% de penalidade aplicável)
        fator_instabilidade = self.jitter_ewma_ms / 500.0

        # Limitamos a penalidade a no máximo 40% de corte na vazão para evitar degradação excessiva
        penalidade_maxima = 0.40
        fator_penalidade = min(fator_instabilidade, penalidade_maxima)

        # Banda efetiva (banda medida descontando o risco da instabilidade) usada nas duas fases abaixo
        banda_efetiva_kbps = self.bandwidth_kbps * (1.0 - fator_penalidade)

        print(f"    [Heurística] Banda Nominal: {self.bandwidth_kbps:.2f} kbps | Jitter EWMA: {self.jitter_ewma_ms:.2f} ms | Banda Efetiva: {banda_efetiva_kbps:.2f} kbps")

        nivel_buffer = self.buffer.nivel_atual_s
        LIMITE_CONFORTO_S = 24

        if nivel_buffer >= LIMITE_CONFORTO_S:
            self.fase_arranque_ativa = False

        if self.fase_arranque_ativa:
            # Fase de Arranque: igual ao Rate-Based, mas usando a banda já penalizada pelo jitter
            self.qualidade_escolhida = representacoes[0]
            for rep in representacoes:
                if banda_efetiva_kbps >= rep["bitrate_kbps"] * margem_seguranca:
                    self.qualidade_escolhida = rep
                else:
                    break
            return

        # Fase de Buffer: mesma lógica de índice e histerese da Política 2 (BBA0)
        BUFFER_MIN = 10.0
        BUFFER_MAX = 30.0

        if nivel_buffer <= BUFFER_MIN:
            novo_indice = 0
        elif nivel_buffer >= BUFFER_MAX:
            novo_indice = len(representacoes) - 1
        else:
            progresso = (nivel_buffer - BUFFER_MIN) / (BUFFER_MAX - BUFFER_MIN)
            novo_indice = round(progresso * (len(representacoes) - 1))

        if self.qualidade_escolhida is not None:
            indice_atual = representacoes.index(self.qualidade_escolhida)
            if novo_indice < indice_atual:
                if nivel_buffer > (BUFFER_MAX * 0.8):
                    novo_indice = indice_atual

        # Teto de Banda usando a vazão JÁ penalizada pelo jitter (diferença em relação à BBA2)
        limite_banda = banda_efetiva_kbps * 1.8
        while novo_indice > 0 and representacoes[novo_indice]['bitrate_kbps'] > limite_banda:
            novo_indice -= 1

        self.qualidade_escolhida = representacoes[novo_indice]


    def executar(self, num_segmentos_simulados=10, nome_arquivo="output/log_baseline.csv", modo_abr="rate_based", margem_seguranca=1):
        """
        Loop principal do player. Fica rodando e baixando os próximos segmentos.
        """
        if not self.baixar_manifesto():
            return

        self.inicializar_csv(nome_arquivo)
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
                match modo_abr:
                    case "rate_based":
                        self.selecionar_qualidade_rate_based(margem_seguranca)
                    case "bba0":
                        self.selecionar_qualidade_buffer_based()
                    case "bba2":
                        # A política do BBA2 mistura o Rate Based com o BBA0
                        # O limite define até quando deve-se usar o Rate-Based
                        LIMITE_CONFORTO_S = 24

                        if self.buffer.nivel_atual_s >= LIMITE_CONFORTO_S:
                            self.fase_arranque_ativa = False

                        if self.fase_arranque_ativa:
                            # Fase de Arranque (início): usa Rate Based
                            self.selecionar_qualidade_rate_based(margem_seguranca)
                        else:
                            # Fase de Estabilidade: usa o BBA0
                            self.selecionar_qualidade_buffer_based()
                    case "heuristica":
                        # Nova Política 3 que utiliza a média móvel do Jitter
                        self.selecionar_qualidade_heuristica_jitter(margem_seguranca)

                LIMITE_MAX_BUFFER = 30.0 
                
                if self.buffer.nivel_atual_s > LIMITE_MAX_BUFFER:
                    # Calcula quanto tempo o player deve esperar para "gastar" o excesso
                    excesso = self.buffer.nivel_atual_s - LIMITE_MAX_BUFFER
                    
                    # O wait máximo é a duração de um segmento, para não dormir demais
                    wait = min(excesso, duracao_segmento_s)
                    
                    print(f"    [Playback] Buffer cheio! Simulando o usuário assistindo... (Dormindo {wait:.2f}s)")
                    time.sleep(wait)
                    
                    # Desconta do buffer o tempo que o usuário passou assistindo
                    self.buffer.nivel_atual_s -= wait

            else:
                print("    Falha crítica ao baixar segmento. Interrompendo streaming.")
                break


if __name__ == '__main__':
    urls_de_bootstrap = [
        "http://137.131.178.229:8080",
        "http://137.131.178.229:8081"
    ]
    
    # 1. Define os valores padrão caso você rode sem parâmetros
    nome_teste = "teste_padrao"
    modo_escolhido = "rate_based"
    margem_escolhida = 1
    
    # 2. Lê os argumentos digitados no terminal
    if len(sys.argv) > 1:
        nome_teste = sys.argv[1]        # Ex: teste_morte_lenta
    if len(sys.argv) > 2:
        modo_escolhido = sys.argv[2]    # Ex: bba0, bba2, heuristica
    if len(sys.argv) > 3:
        margem_escolhida = float(sys.argv[3])  # Ex: 1.2 (20%)

    # 3. Monta a nova hierarquia de pastas
    pasta_saida = f"output/{nome_teste}/{modo_escolhido}"
    
    # O arquivo sempre se chamará 'log.csv' dentro da pasta respectiva
    caminho_saida = f"{pasta_saida}/log.csv"

    cliente = ClienteDash(urls_de_bootstrap)
    cliente.executar(num_segmentos_simulados=60, nome_arquivo=caminho_saida, modo_abr=modo_escolhido, margem_seguranca=margem_escolhida)

    gerador = GeradorGraficos(caminho_saida)
    gerador.gerar_grafico_padrao()
    gerador.gerar_grafico_com_jitter()