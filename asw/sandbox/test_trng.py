#
# NIST SP 800-90A
#
import time
import secrets
import hashlib
import binascii
import os

def measure_time(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"Функция '{func.__name__}' выполнилась за {end - start:.5f} сек")
        return result
    return wrapper

###############################################################################
#@measure_time
def trng_simple(num_bytes=32):
    """
    Генерация истинно случайных байтов используя системную энтропию
    """
    random_bytes = secrets.token_bytes(num_bytes)


    test_randomness(random_bytes)
    return random_bytes

###############################################################################
#@measure_time
def trng_time(num_bytes=32):
    """
    TRNG на основе микросекундных временных меток
    """
    entropy_pool = bytearray()
    
    for _ in range(num_bytes):  # Собираем 100 измерений
        # Время с максимально возможной точностью
        micro_time = time.time_ns() % 1000000
        entropy_pool.extend(micro_time.to_bytes(4, 'little'))
        time.sleep(0.001)  # Минимальная задержка
    
    # Хешируем для улучшения распределения
    ret = hashlib.sha256(entropy_pool).digest()
    test_randomness(ret)
    return ret

###############################################################################
#@measure_time
def trng_combined(size=32):
    """
    Комбинированный TRNG из нескольких источников
    """
    entropy_sources = []
    
    # 1. Системный источник
    entropy_sources.append(os.urandom(size))
    
    # 2. Временной источник
    time_entropy = str(time.time_ns()).encode()
    entropy_sources.append(hashlib.sha256(time_entropy).digest())
    
    # 3. PID и идентификаторы процесса
    process_entropy = str(os.getpid()).encode() + str(os.getppid()).encode()
    entropy_sources.append(hashlib.sha256(process_entropy).digest())
    
    # Смешиваем все источники
    combined = b''.join(entropy_sources)
    final_random = hashlib.sha512(combined).digest()[:size]
    test_randomness(final_random);
    return final_random

###############################################################################

def test_randomness(data, num_samples=1000):
    """
    Простой тест на случайность
    """
    if len(data) < num_samples:
        return "Недостаточно данных"
    
    # Проверка распределения битов
    ones = sum(bin(byte).count('1') for byte in data[:num_samples])
    zeros = num_samples * 8 - ones
    
    ratio = ones / (zeros + ones)
    print(f"Соотношение 1/0: {ratio:.3f} (идеально 0.5)")
    
    if 0.45 <= ratio <= 0.55:
        return "Хорошее распределение"
    else:
        return "Возможные проблемы с распределением"

print()
print("=== TRNG Генерация ===")

a1 = trng_simple(32)
a2 = trng_time(32)
a3 = trng_combined(32)

print()
print(f"TRNG байты: {binascii.hexlify(a1).decode()}" )
print(f"TRNG байты: {binascii.hexlify(a2).decode()}" )
print(f"TRNG байты: {binascii.hexlify(a3).decode()}" )
print()

generators = {
    "os_urandom"    : lambda size: os.urandom(size),
    "secrets"       : lambda size: secrets.token_bytes(size),
    "trng_simple"   : trng_simple,
    "trng_time"     : trng_time,
    "trng_combined" : trng_combined
}

def benchmark_trng(generators, sizes=[16, 32, 64,128,256], runs=1000):
    """
    Сравнение скорости разных TRNG
    """
    
    results = {}
    
    for name, generator in generators.items():
        print(f"\n🔍 Тестируем {name}...")
        
        for size in sizes:
            times = []
            
            # Прогрев
            for _ in range(10):
                generator(size)
            
            # Основные замеры
            for _ in range(runs):
                start = time.perf_counter()
                generator(size)
                end = time.perf_counter()
                times.append((end - start) * 1000)  # в миллисекундах
            
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            results[f"{name}_{size}"] = avg_time
            
            print(f"  Размер {size:2d} байт: {avg_time:.6f} мс " f"(min: {min_time:.6f}, max: {max_time:.6f})")
    
    return results

results = benchmark_trng(generators, runs=10)