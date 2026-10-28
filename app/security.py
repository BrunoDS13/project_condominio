import threading
import time


class LoginThrottle:
    """Limita tentativas de login falhas por e-mail e por IP (em memória, por processo)."""

    MAX_POR_EMAIL = 5
    MAX_POR_IP = 20
    JANELA = 15 * 60  # segundos

    def __init__(self):
        self._falhas = {}
        self._lock = threading.Lock()

    def _recentes(self, chave):
        agora = time.time()
        recentes = [t for t in self._falhas.get(chave, []) if agora - t < self.JANELA]
        self._falhas[chave] = recentes
        return recentes

    def segundos_restantes(self, ip, email):
        """0 se liberado; senão, quantos segundos faltam para nova tentativa."""
        with self._lock:
            espera = 0
            for chave, maximo in ((f"e:{email}", self.MAX_POR_EMAIL), (f"i:{ip}", self.MAX_POR_IP)):
                recentes = self._recentes(chave)
                if len(recentes) >= maximo:
                    espera = max(espera, int(self.JANELA - (time.time() - recentes[0])) + 1)
            return espera

    def falhou(self, ip, email):
        with self._lock:
            for chave in (f"e:{email}", f"i:{ip}"):
                self._recentes(chave).append(time.time())

    def sucesso(self, email):
        with self._lock:
            self._falhas.pop(f"e:{email}", None)
