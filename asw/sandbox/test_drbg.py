import os
import secrets
import hashlib
import hmac
from Crypto.Cipher import AES

###############################################################################

# DRBG - детерминированная генерация на основе种子 (seed)
def simple_hash_drbg(seed, length):
    result = b''
    counter = 0
    while len(result) < length:
        # Используем HMAC для генерации
        data    = seed + counter.to_bytes(4, 'big')
        chunk   = hashlib.sha256(data).digest() # ← ПРЯМОЙ вызов SHA-256!
        result  += chunk
        counter += 1
    return result[:length]

###############################################################################

def simple_cbc_drbg(seed, length):
    """
    CBC_DRBG - детерминированная генерация в режиме CBC
    """
    # Инициализация
    key     = hashlib.sha256(seed + b"key").digest()[:16]   # Деривация ключа из seed
    iv      = hashlib.sha256(seed + b"iv").digest()[:16]    # Деривация IV из seed 
    cipher  = AES.new(key, AES.MODE_ECB)                    # Создание AES шифра
    
    result          = b''   # Буфер для результата
    block_previous  = iv    # Текущий блок цепочки = IV
    block_count     = 0     # Счетчик блоков
    
    ##
    ## health checks
    ##
    health_last_block       = None
    health_identical_count  = 0
    
    while len(result) < length:
        # В CBC режиме: шифруем (предыдущий_блок XOR данные)
        # Для DRBG данные могут быть счетчиком или нулями
        data = block_count.to_bytes(16, 'big')  # 16 байт данных
        
        # Шифруем блок
        # XOR с предыдущим блоком
        block_to_encrypt = bytes(a ^ b for a, b in zip(block_previous, data))
        encrypted_block = cipher.encrypt(block_to_encrypt)
        result += encrypted_block
        
        ##
        ## Health check: идентичные блоки
        ##
        if encrypted_block == health_last_block:
            health_identical_count += 1
            if health_identical_count > 2:
                print(f"Health check failed: {health_identical_count} identical blocks")
        else:
            health_identical_count = 0
        health_last_block = encrypted_block

        # Обновляем предыдущий блок для цепочки
        block_previous = encrypted_block
        block_count += 1
        
        ##
        ## Health check: распределение битов
        ##
        final_result= result[:length]
        ones_count  = sum(bin(byte).count('1') for byte in final_result)
        total_bits  = len(final_result) * 8
        ones_ratio  = ones_count / total_bits
        
        if ones_ratio < 0.4 or ones_ratio > 0.6:
            print(f"Health warning: Suspicious bit distribution {ones_ratio:.3f}")    

    return result[:length]

###############################################################################

def simple_hmac_drbg(seed,length,personalization=b""):
    """
    HMAC_DRBG - детерминированная генерация на основе HMAC

        Перемешивание энтропии      : Seed проходит через multiple HMAC-раунды
        Зависимость от контекста    : Personalization строка делает каждый DRBG уникальным
        Разрушение паттернов        : Даже структурированный seed становится неотличим от случайного
        Защита от компрометации     : Сложнее анализировать внутреннее состояние
        Стандартизация              : NIST SP 800-90A требует именно такой инициализации
    
    """
    # Шаг 1: Инициализация
    key     = b'\x00' * 32          # Начальный ключ (32 байта для SHA-256)
    value   =  b'\x01' * 32         # Начальное значение
    
    # Шаг 2.0: 
    key     = hmac.new(key,value + b'\x00'+seed+personalization,hashlib.sha256).digest()
    value   = hmac.new(key,value,hashlib.sha256).digest()
    # Шаг 2.1: 
    key = hmac.new(key,value+b'\x01'+seed+personalization,hashlib.sha256).digest()
    value = hmac.new(key,value,hashlib.sha256).digest()

    # Шаг 3: Генерация
    result = b''
    while (len(result) < length):
        value = hmac.new(key,value, hashlib.sha256).digest()
        result+=value

    return result[:length]


true_random = secrets.token_bytes(16)   # Используем TRNG как seed для DRBG

print(f"TRNG        : {true_random.hex()}")
print(f"HASH_DRBG   : {simple_hash_drbg(true_random, 64).hex()}")
print(f"HMAC_DRBG   : {simple_hmac_drbg(true_random,64).hex()}")
print(f"CBC_DRBG    : {simple_cbc_drbg(true_random,64).hex()}")
