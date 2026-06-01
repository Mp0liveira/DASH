class BufferManager:
    def __init__(self):
        self.nivel_atual_s = 0.0

    def processar_download(self, tempo_download_s, duracao_segmento_s):
        """
        Calcula o consumo do buffer durante o download e adiciona o novo segmento.
        Retorna se o buffer foi suficiente e quanto tempo o vídeo ficou travado (stall).
        """
        buffer_can_play = 1
        stall_duration_s = 0.0

        # O player consumiu vídeo enquanto o download acontecia
        if self.nivel_atual_s >= tempo_download_s:
            # Tinha buffer suficiente, o vídeo rodou liso
            self.nivel_atual_s -= tempo_download_s
        else:
            # O download demorou mais do que o buffer aguentava, o vídeo trava
            buffer_can_play = 0
            stall_duration_s = tempo_download_s - self.nivel_atual_s
            self.nivel_atual_s = 0.0  # Buffer zerou

        # O download terminou, o novo trecho de vídeo entra no buffer
        self.nivel_atual_s += duracao_segmento_s

        print(f"    [Buffer] Nível atual: {self.nivel_atual_s:.2f}s | Travou? {'Não' if buffer_can_play else f'Sim ({stall_duration_s:.2f}s)'}")
        
        return buffer_can_play, stall_duration_s