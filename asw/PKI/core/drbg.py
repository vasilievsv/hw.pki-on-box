class NISTDRBG:
    """DRBG по стандарту NIST SP 800-90A"""
    def __init__(self, trng: HardwareTRNG):
        self.trng = trng
        self.initialized = False
        
    def instantiate(self, personalization_string=b""):
        # Инициализация DRBG
        entropy = self.trng.get_entropy(32)
        self._initialize_drbg(entropy, personalization_string)
        
    def generate(self, num_bytes: int) -> bytes:
        # Генерация псевдослучайных данных
        if not self.initialized:
            raise RuntimeError("DRBG not initialized")
        return self._generate_bytes(num_bytes)