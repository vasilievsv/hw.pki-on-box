#
# Хи-квадрат (χ²) - это число, которое показывает, насколько ваши данные отличаются от идеального равномерного распределения.
# Хи-квадрат - это метр равномерности. Чем меньше - тем лучше случайные числа! 
#
# Суть в трех пунктах:
# Сравниваем - что получили vs что ожидали
# Суммируем - общая степень неравномерности

import matplotlib.pyplot as plt
import numpy as np
import os

def interpret_chi_square(chi_squared, num_bins=256):
    """Интерпретация значения хи-квадрат"""
    
    degrees_of_freedom = num_bins - 1
    
    # Критические значения для 255 степеней свободы
    if chi_squared < 293:
        return "✅ Отличное равномерное распределение"
    elif chi_squared < 310:
        return "⚠️  Хорошее распределение" 
    elif chi_squared < 330:
        return "❌ Умеренные проблемы с равномерностью"
    else:
        return "💥 Серьезные проблемы с распределением"

def calculate_chi_square(data, num_bins=256):
    """Вычисление хи-квадрат для случайных чисел"""
    
    # Преобразуем данные в числа 0-255
    if isinstance(data, bytes):
        values = list(data)
    else:
        values = [x if isinstance(x, int) else int.from_bytes(x, 'big') 
                 for x in data]
    
    # Создаем гистограмму
    observed, bins = np.histogram(values, bins=num_bins, range=(0, 255))
    
    # Ожидаемое значение для равномерного распределения
    expected = len(values) / num_bins
    
    # Вычисляем хи-квадрат
    chi_squared = np.sum((observed - expected) ** 2 / expected)
    
    return chi_squared

def visualize_chi_square():
    """Визуализация концепции хи-квадрат"""
    
    # Идеальное распределение
    perfect = [100] * 10
    
    # Реальные распределения
    good = [98, 102, 101, 99, 100, 100, 99, 101, 102, 98]
    bad = [150, 50, 120, 80, 130, 70, 140, 60, 110, 90]
    
    plt.figure(figsize=(12, 4))
    
    # Идеальное
    plt.subplot(1, 3, 1)
    plt.bar(range(10), perfect, color='green', alpha=0.7)
    plt.title('Идеальное распределение\nχ² = 0.00')
    plt.ylim(0, 160)
    
    # Хорошее
    plt.subplot(1, 3, 2)
    plt.bar(range(10), good, color='blue', alpha=0.7)
    chi_good = sum((g - 100) ** 2 / 100 for g in good)
    plt.title(f'Хорошее распределение\nχ² = {chi_good:.2f}')
    plt.ylim(0, 160)
    
    # Плохое
    plt.subplot(1, 3, 3)
    plt.bar(range(10), bad, color='red', alpha=0.7)
    chi_bad = sum((b - 100) ** 2 / 100 for b in bad)
    plt.title(f'Плохое распределение\nχ² = {chi_bad:.2f}')
    plt.ylim(0, 160)
    
    plt.tight_layout()
    plt.show()

#visualize_chi_square()

# # Пример с хорошим генератором
# good_data = [np.random.randint(0, 256) for _ in range(10000)]
# chi_good = calculate_chi_square(good_data)
# print(f"Хороший генератор: χ² = {chi_good:.2f}")

# # Пример с плохим генератором (только четные числа)
# bad_data = [i * 2 % 256 for i in range(10000)]
# chi_bad = calculate_chi_square(bad_data) 
# print(f"Плохой генератор: χ² = {chi_bad:.2f}")



# Использование в тестах
data = os.urandom(10000)
chi_val = calculate_chi_square(data)
assessment = interpret_chi_square(chi_val)

print(f"Хи-квадрат: {chi_val:.2f}")
print(f"Оценка: {assessment}")