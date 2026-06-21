import pandas as pd
import matplotlib.pyplot as plt

class GeradorGraficos:
    def __init__(self, arquivo_csv):
        """
        Recebe o caminho do arquivo CSV que será lido para gerar os gráficos.
        """
        self.arquivo_csv = arquivo_csv

    def gerar_grafico_vazao_qualidade(self):
        print("\n[*] Gerando gráfico de Vazão vs Qualidade...")
        try:
            df = pd.read_csv(self.arquivo_csv)
            
            plt.figure(figsize=(10, 5))
            
            # Plota a Vazão da rede (linha com bolinhas)
            plt.plot(df['segmento'], df['vazao_kbps'], label='Vazão Medida (kbps)', color='blue', marker='o', alpha=0.6)
            
            # Plota a Qualidade escolhida (linha em degraus)
            plt.step(df['segmento'], df['bitrate_kbps'], label='Qualidade Escolhida (kbps)', color='red', where='post', linewidth=2)
            
            plt.title('Baseline: Vazão da Rede vs Qualidade do Vídeo')
            plt.xlabel('Número do Segmento')
            plt.ylabel('Taxa (kbps)')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.legend()
            
            # Salva com sufixo '_vazao' para não sobrescrever outros gráficos
            caminho_grafico = self.arquivo_csv.replace('.csv', '_vazao.png')
            plt.savefig(caminho_grafico)
            plt.close() # Fecha a figura para liberar memória
            print(f"    [+] Gráfico de vazão salvo em: {caminho_grafico}")
            
        except Exception as e:
            print(f"    [!] Erro ao gerar gráfico de vazão: {e}")

    def gerar_grafico_buffer(self):
        print("[*] Gerando gráfico unificado: Vazão, Qualidade e Buffer (com trocas de servidor)...")
        try:
            df = pd.read_csv(self.arquivo_csv)
            
            # Cria a figura e o Eixo Principal (ax1) para o Buffer
            fig, ax1 = plt.subplots(figsize=(12, 6))
            
            # --- EIXO Y DA ESQUERDA (NÍVEL DO BUFFER EM SEGUNDOS) ---
            cor_buffer = 'tab:green'
            ax1.set_xlabel('Número do Segmento')
            ax1.set_ylabel('Nível do Buffer (segundos)', color=cor_buffer, fontweight='bold')
            ax1.plot(df['segmento'], df['buffer_level_s'], color=cor_buffer, marker='s', linewidth=2, label='Nível do Buffer (s)')
            ax1.tick_params(axis='y', labelcolor=cor_buffer)
            ax1.grid(True, linestyle='--', alpha=0.6)
            
            # Destacar os travamentos com um "X" vermelho no eixo do buffer
            travamentos = df[df['rebuffer_event'] == 1]
            if not travamentos.empty:
                ax1.scatter(travamentos['segmento'], travamentos['buffer_level_s'], 
                            color='red', s=150, zorder=5, marker='X', label='Travamento (Stall)')

            # --- DETECÇÃO E PLOTAGEM DA TROCA DE SERVIDORES ---
            if 'server_id' in df.columns and len(df) > 1:
                # Identifica onde o server_id mudou em relação ao segmento anterior
                df['trocou_servidor'] = df['server_id'] != df['server_id'].shift()
                # O primeiro registro sempre será True no shift, então forçamos para False
                df.loc[df.index[0], 'trocou_servidor'] = False
                
                # Filtra apenas as linhas onde houve a troca
                linhas_troca = df[df['trocou_servidor']]
                
                print_label = True
                for _, row in linhas_troca.iterrows():
                    # O label só é definido na primeira linha vertical para não duplicar na legenda
                    label_vlinha = 'Troca de Servidor' if print_label else ""
                    ax1.axvline(x=row['segmento'], color='purple', linestyle='--', linewidth=1.8, 
                                alpha=0.8, zorder=4, label=label_vlinha)
                    print_label = False

            # --- EIXO Y DA DIREITA (TAXAS EM KBPS) ---
            ax2 = ax1.twinx()  # Cria o segundo eixo Y compartilhando o mesmo eixo X
            ax2.set_ylabel('Taxa (kbps)', color='black', fontweight='bold')
            
            # 1. Plota a Vazão Medida (linha com bolinhas azuis)
            ax2.plot(df['segmento'], df['vazao_kbps'], color='blue', marker='o', alpha=0.4, label='Vazão Medida (kbps)')
            
            # 2. Plota a Qualidade Escolhida (linha em degraus vermelha)
            ax2.step(df['segmento'], df['bitrate_kbps'], color='red', where='post', linewidth=2.5, alpha=0.8, label='Qualidade (kbps)')
            ax2.tick_params(axis='y', labelcolor='black')

            # --- AJUSTES FINAIS E LEGENDA ---
            # Junta as legendas dos dois eixos em um único quadro
            linhas1, labels1 = ax1.get_legend_handles_labels()
            linhas2, labels2 = ax2.get_legend_handles_labels()
            # Coloca a legenda fora do caminho das linhas (no topo à esquerda, com fundo levemente transparente)
            ax1.legend(linhas1 + linhas2, labels1 + labels2, loc='upper left', bbox_to_anchor=(0.02, 0.98), facecolor='white', framealpha=0.9)

            plt.title('Dinâmica do Player: Vazão da Rede, Qualidade Escolhida e Nível do Buffer', fontsize=14)
            
            # Ajusta o layout para evitar cortes
            fig.tight_layout()
            
            # Salva o arquivo
            caminho_grafico = self.arquivo_csv.replace('.csv', '_analise_completa.png')
            plt.savefig(caminho_grafico)
            plt.close()
            print(f"    [+] Gráfico de análise completa salvo em: {caminho_grafico}")
            
        except Exception as e:
            print(f"    [!] Erro ao gerar gráfico completo: {e}")