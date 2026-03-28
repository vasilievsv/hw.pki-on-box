#include "main.h"

void Error_Handler(void) { while (1) {} }

void SystemClock_Config(void);

int main(void) {
    HAL_Init();
    SystemClock_Config();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    GPIO_InitTypeDef gpio = {GPIO_PIN_6, GPIO_MODE_OUTPUT_PP,
                             GPIO_NOPULL, GPIO_SPEED_FREQ_LOW};
    HAL_GPIO_Init(GPIOC, &gpio);
    while (1) {
        HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_6);
        HAL_Delay(500);
    }
}
