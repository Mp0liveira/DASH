import pandas as pd
import matplotlib.pyplot as plt

class GeradorGraficos:
    def __init__(self, arquivo_csv):
        self.arquivo_csv = arquivo_csv

    def gerar_grafico_vazao_qualidade(self):
        # (Mantenha o seu código original desta função aqui, se ainda usar)
        pass

    def gerar_grafico_padrao(self):
        """
        Gera o gráfico clássico (Cenários 1 e 2): Apenas Buffer, Vazão e Qualidade.
        """
        print("[*] Gerando gráfico Padrão (Sem Jitter)...")
        try:
            df = pd.read_csv(self.arquivo_csv)
            fig, ax1 = plt.subplots(figsize=(12, 6))
            
            # --- EIXO Y DA ESQUERDA (BUFFER) ---
            cor_buffer = 'tab:green'
            ax1.set_xlabel('Número do Segmento')
            ax1.set_ylabel('Nível do Buffer (segundos)', color=cor_buffer, fontweight='bold')
            ax1.plot(df['segmento'], df['buffer_level_s'], color=cor_buffer, marker='s', linewidth=2, label='Nível do Buffer (s)')
            ax1.tick_params(axis='y', labelcolor=cor_buffer)
            ax1.grid(True, linestyle='--', alpha=0.6)
            
            # Travamentos (Stalls)
            travamentos = df[df['rebuffer_event'] == 1]
            if not travamentos.empty:
                ax1.scatter(travamentos['segmento'], travamentos['buffer_level_s'], color='red', s=150, zorder=5, marker='X', label='Travamento (Stall)')

            # Troca de Servidor
            if 'server_id' in df.columns and len(df) > 1:
                df['trocou_servidor'] = df['server_id'] != df['server_id'].shift()
                df.loc[df.index[0], 'trocou_servidor'] = False
                linhas_troca = df[df['trocou_servidor']]
                print_label = True
                for _, row in linhas_troca.iterrows():
                    label_vlinha = 'Troca de Servidor' if print_label else ""
                    ax1.axvline(x=row['segmento'], color='purple', linestyle='--', linewidth=1.8, alpha=0.8, zorder=4, label=label_vlinha)
                    print_label = False

            # --- EIXO Y DA DIREITA (TAXAS) ---
            ax2 = ax1.twinx()  
            ax2.set_ylabel('Taxa (kbps)', color='black', fontweight='bold')
            ax2.plot(df['segmento'], df['vazao_kbps'], color='blue', marker='o', alpha=0.4, label='Vazão Medida (kbps)')
            ax2.step(df['segmento'], df['bitrate_kbps'], color='red', where='post', linewidth=2.5, alpha=0.8, label='Qualidade (kbps)')
            ax2.tick_params(axis='y', labelcolor='black')

            # --- LEGENDA E SALVAMENTO ---
            linhas1, labels1 = ax1.get_legend_handles_labels()
            linhas2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(linhas1 + linhas2, labels1 + labels2, loc='upper left', bbox_to_anchor=(0.02, 0.98), facecolor='white', framealpha=0.9)

            plt.title('Dinâmica do Player: Vazão da Rede, Qualidade Escolhida e Nível do Buffer', fontsize=14)
            fig.tight_layout()
            
            caminho_grafico = self.arquivo_csv.replace('.csv', '_grafico_padrao.png')
            plt.savefig(caminho_grafico)
            plt.close()
            print(f"    [+] Gráfico salvo: {caminho_grafico}")
            
        except Exception as e:
            print(f"    [!] Erro ao gerar gráfico padrão: {e}")

    def gerar_grafico_com_jitter(self):
        """
        Gera o gráfico avançado (Cenário 3): Inclui o 3º eixo com a Nuvem de Jitter.
        """
        print("[*] Gerando gráfico Avançado (Com Jitter)...")
        try:
            df = pd.read_csv(self.arquivo_csv)
            fig, ax1 = plt.subplots(figsize=(12, 6))
            
            # --- EIXO Y DA ESQUERDA (BUFFER) ---
            cor_buffer = 'tab:green'
            ax1.set_xlabel('Número do Segmento')
            ax1.set_ylabel('Nível do Buffer (segundos)', color=cor_buffer, fontweight='bold')
            ax1.plot(df['segmento'], df['buffer_level_s'], color=cor_buffer, marker='s', linewidth=2, label='Nível do Buffer (s)')
            ax1.tick_params(axis='y', labelcolor=cor_buffer)
            ax1.grid(True, linestyle='--', alpha=0.6)
            
            # Travamentos (Stalls)
            travamentos = df[df['rebuffer_event'] == 1]
            if not travamentos.empty:
                ax1.scatter(travamentos['segmento'], travamentos['buffer_level_s'], color='red', s=150, zorder=5, marker='X', label='Travamento (Stall)')

            # Troca de Servidor
            if 'server_id' in df.columns and len(df) > 1:
                df['trocou_servidor'] = df['server_id'] != df['server_id'].shift()
                df.loc[df.index[0], 'trocou_servidor'] = False
                linhas_troca = df[df['trocou_servidor']]
                print_label = True
                for _, row in linhas_troca.iterrows():
                    label_vlinha = 'Troca de Servidor' if print_label else ""
                    ax1.axvline(x=row['segmento'], color='purple', linestyle='--', linewidth=1.8, alpha=0.8, zorder=4, label=label_vlinha)
                    print_label = False

            # --- EIXO Y DA DIREITA (TAXAS) ---
            ax2 = ax1.twinx()  
            ax2.set_ylabel('Taxa (kbps)', color='black', fontweight='bold')
            ax2.plot(df['segmento'], df['vazao_kbps'], color='blue', marker='o', alpha=0.4, label='Vazão Medida (kbps)')
            ax2.step(df['segmento'], df['bitrate_kbps'], color='red', where='post', linewidth=2.5, alpha=0.8, label='Qualidade (kbps)')
            ax2.tick_params(axis='y', labelcolor='black')

            # --- 3º EIXO Y (JITTER EWMA) ---
            linhas3, labels3 = [], []
            if 'jitter_ewma_ms' in df.columns:
                ax3 = ax1.twinx()
                ax3.spines['right'].set_position(('outward', 60))
                ax3.set_ylabel('Instabilidade / Jitter (ms)', color='darkorange', fontweight='bold')
                ax3.fill_between(df['segmento'], df['jitter_ewma_ms'], color='orange', alpha=0.15)
                ax3.plot(df['segmento'], df['jitter_ewma_ms'], color='darkorange', linestyle=':', linewidth=1.5, label='Jitter EWMA (ms)')
                ax3.tick_params(axis='y', labelcolor='darkorange')
                
                max_jitter = df['jitter_ewma_ms'].max()
                if max_jitter > 0:
                    ax3.set_ylim(0, max_jitter * 2.5) 
                linhas3, labels3 = ax3.get_legend_handles_labels()

            # --- LEGENDA E SALVAMENTO ---
            linhas1, labels1 = ax1.get_legend_handles_labels()
            linhas2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(linhas1 + linhas2 + linhas3, labels1 + labels2 + labels3, loc='upper left', bbox_to_anchor=(0.02, 0.98), facecolor='white', framealpha=0.9)

            plt.title('Dinâmica do Player: Adaptação de Mídia e Instabilidade da Rede', fontsize=14)
            fig.tight_layout()
            
            caminho_grafico = self.arquivo_csv.replace('.csv', '_grafico_com_jitter.png')
            plt.savefig(caminho_grafico, bbox_inches='tight')
            plt.close()
            print(f"    [+] Gráfico salvo: {caminho_grafico}")
            
        except Exception as e:
            print(f"    [!] Erro ao gerar gráfico avançado: {e}")