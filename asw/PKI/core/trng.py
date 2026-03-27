# core/trng.py
class HardwareTRNG:
    """Аппаратный TRNG (эмуляция для обучения)"""
    def __init__(self, source="/dev/random"):  # или ваше железо
        self.source = source
    
    def get_entropy(self, num_bytes: int) -> bytes:
        # Реализация сбора энтропии
        pass