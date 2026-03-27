import os
import time
import hashlib
import collections
import numpy as np
import secrets
from matplotlib import pyplot as plt

def basic_distribution_test(data, test_name="Тест"):
    """Базовые тесты распределения"""
    print(f"\n📊 {test_name}")
    print("=" * 50)
    
    if len(data) == 0:
        print("❌ Нет данных для тестирования")
        return
    
    # Преобразуем в байты если это не байты
    if isinstance(data[0], int):
        byte_data = bytes(data)
    else:
        byte_data = b''.join(data) if isinstance(data[0], bytes) else data
    
    # Статистика по битам
    ones = sum(bin(byte).count('1') for byte in byte_data)
    zeros = len(byte_data) * 8 - ones
    bit_ratio = ones / (len(byte_data) * 8)
    
    print(f"Биты: 1={ones}, 0={zeros}, соотношение={bit_ratio:.4f}")
    print(f"Идеальное соотношение: 0.5000")
    print(f"Отклонение: {abs(bit_ratio - 0.5):.4f}")
    
    # Оценка качества
    if 0.49 <= bit_ratio <= 0.51:
        print("✅ Отличное распределение битов")
    elif 0.48 <= bit_ratio <= 0.52:
        print("⚠️  Хорошее распределение битов") 
    else:
        print("❌ Плохое распределение битов")
    
    return bit_ratio

def advanced_distribution_analysis(data, bin_count=256):
    """Расширенный анализ распределения"""
    
    if isinstance(data, bytes):
        values = list(data)
    else:
        values = [int.from_bytes(chunk, 'big') for chunk in data] if isinstance(data[0], bytes) else data
    
    print(f"\n🔍 Расширенный анализ ({len(values)} samples)")
    print("=" * 50)
    
    # Базовая статистика
    mean = np.mean(values)
    std = np.std(values)
    unique = len(set(values))
    
    print(f"Среднее: {mean:.2f} (идеально ~127.5)")
    print(f"Стандартное отклонение: {std:.2f}")
    print(f"Уникальных значений: {unique}/{len(values)}")
    
    # Тест на равномерность (хи-квадрат)
    observed, _ = np.histogram(values, bins=bin_count, range=(0, 255))
    expected = [len(values) / bin_count] * bin_count
    chi_squared = np.sum((observed - expected) ** 2 / expected)
    
    print(f"Хи-квадрат: {chi_squared:.2f}")
    
    # Оценка
    if chi_squared < 300:
        print("✅ Отличная равномерность")
    elif chi_squared < 500:
        print("⚠️  Хорошая равномерность")
    else:
        print("❌ Плохая равномерность")
    
    return {
        'mean': mean,
        'std': std, 
        'unique_ratio': unique / len(values),
        'chi_squared': chi_squared
    }

def plot_distribution(data, title="Распределение случайных чисел"):
    """Визуализация распределения"""
    
    if isinstance(data, bytes):
        values = list(data)
    else:
        values = [int.from_bytes(chunk, 'big') for chunk in data] if isinstance(data[0], bytes) else data
    
    plt.figure(figsize=(15, 5))
    
    # Гистограмма
    plt.subplot(1, 3, 1)
    plt.hist(values, bins=50, alpha=0.7, color='blue', edgecolor='black')
    plt.title(f'{title}\nГистограмма')
    plt.xlabel('Значение')
    plt.ylabel('Частота')
    plt.grid(True, alpha=0.3)
    
    # Последовательность значений
    plt.subplot(1, 3, 2)
    plt.plot(values[:200], 'o-', alpha=0.7, markersize=2)
    plt.title('Последовательность (первые 200)')
    plt.xlabel('Позиция')
    plt.ylabel('Значение')
    plt.grid(True, alpha=0.3)
    
    # Автокорреляция
    plt.subplot(1, 3, 3)
    autocorr = np.correlate(values, values, mode='full')
    autocorr = autocorr[len(autocorr)//2:]
    autocorr = autocorr / autocorr[0]  # Нормализация
    plt.plot(autocorr[:100])
    plt.title('Автокорреляция')
    plt.xlabel('Лаг')
    plt.ylabel('Корреляция')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

def test_trng_generators(generators, sample_size=10000):
    """Тестирование нескольких TRNG генераторов"""
    
    results = {}
    
    for name, generator in generators.items():
        print(f"\n🎯 Тестируем {name}")
        print("=" * 50)
        
        # Генерация данных
        start_time = time.time()
        
        if name in ['os_urandom', 'secrets']:
            data = generator(sample_size)
        else:
            data = [generator(32) for _ in range(sample_size // 32)]
        
        gen_time = 1 #= time.time() - start_time
        
        print(f"Время генерации: {gen_time:.4f} сек")
        print(f"Скорость: {sample_size / gen_time:.0f} байт/сек")
        
        # Запуск тестов
        bit_ratio = basic_distribution_test(data, f"Базовый тест - {name}")
        stats = advanced_distribution_analysis(data)
        
        results[name] = {
            'bit_ratio': bit_ratio,
            'stats': stats,
            'gen_time': gen_time
        }
        
        # Визуализация для первых 3 генераторов
        if len(results) <= 3:
            plot_distribution(data, f"Распределение - {name}")
    
    return results

def compare_generators(results):
    """Сравнительный анализ генераторов"""
    
    print("\n🏆 СРАВНИТЕЛЬНАЯ ТАБЛИЦА")
    print("=" * 80)
    print(f"{'Генератор':<15} {'Биты 1/0':<10} {'Среднее':<10} {'StdDev':<10} {'Хи-квадрат':<12} {'Скорость':<12}")
    print("-" * 80)
    
    best_score = float('inf')
    best_generator = None
    
    for name, result in results.items():
        bit_ratio = result['bit_ratio']
        stats = result['stats']
        speed = result['gen_time']
        
        # Оценка качества (меньше = лучше)
        score = (
            abs(bit_ratio - 0.5) * 1000 +  # Отклонение битов
            abs(stats['mean'] - 127.5) / 10 +  # Отклонение среднего
            stats['chi_squared'] / 1000 +  # Хи-квадрат
            speed * 10  # Время
        )
        
        if score < best_score:
            best_score = score
            best_generator = name
        
        print(f"{name:<15} {bit_ratio:.4f}    {stats['mean']:<9.1f} {stats['std']:<9.1f} "
              f"{stats['chi_squared']:<11.1f} {1/speed:<11.0f} байт/с")
    
    print("-" * 80)
    print(f"🎉 ЛУЧШИЙ ГЕНЕРАТОР: {best_generator} (score: {best_score:.2f})")
    
    return best_generator

def run_specialized_tests(generator, name="TRNG"):
    """Специализированные тесты для глубокого анализа"""
    
    print(f"\n🔬 УГЛУБЛЕННЫЕ ТЕСТЫ ДЛЯ {name}")
    
    # Тест на повторяющиеся последовательности
    samples = [generator(32) for _ in range(1000)]
    unique_samples = len(set(samples))
    print(f"Уникальность: {unique_samples}/1000 samples")
    
    # Тест на монотонность
    values = [int.from_bytes(generator(4), 'big') for _ in range(100)]
    monotonic_increase = sum(1 for i in range(1, len(values)) if values[i] > values[i-1])
    print(f"Монотонность: {monotonic_increase}/99 увеличений")
    
    # Тест на кластеризацию
    clusters = 0
    for i in range(1, len(values)):
        if abs(values[i] - values[i-1]) < 10:  # Близкие значения
            clusters += 1
    print(f"Кластеризация: {clusters}/99 пар")


def fast_trng(size=32):
    entropy = os.urandom(size) + int(time.time_ns()).to_bytes(8, 'little')
    return hashlib.sha256(entropy).digest()[:size]

def ultra_fast_trng(size=32):
    return os.urandom(size)







generators = {
    'os_urandom'    : lambda size: os.urandom(size),
    'secrets'       : lambda size: secrets.token_bytes(size),
}

# Запуск комплексного тестирования
if __name__ == "__main__":
    print("🎲 КОМПЛЕКСНЫЙ ТЕСТ РАСПРЕДЕЛЕНИЯ TRNG")
    print("=" * 60)
    
    results = test_trng_generators(generators, sample_size=50000)
    best = compare_generators(results)