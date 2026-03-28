#include "trng_hid.h"
#include <string.h>

static RNG_HandleTypeDef hrng;

void TRNG_Init(void) {
    /* HSI48 уже включён в SystemClock_Config — переиспользуем для RNG */
    RCC_PeriphCLKInitTypeDef clk = {0};
    clk.PeriphClockSelection = RCC_PERIPHCLK_RNG;
    clk.RngClockSelection    = RCC_RNGCLKSOURCE_HSI48;
    HAL_RCCEx_PeriphCLKConfig(&clk);

    __HAL_RCC_RNG_CLK_ENABLE();
    hrng.Instance = RNG;
    HAL_RNG_Init(&hrng);
}

void TRNG_FillReport(uint8_t *report, uint16_t len) {
    for (uint16_t i = 0; i < len; i += 4) {
        uint32_t rnd;
        HAL_RNG_GenerateRandomNumber(&hrng, &rnd);
        uint16_t copy = ((i + 4) <= len) ? 4 : (len - i);
        memcpy(&report[i], &rnd, copy);
    }
}
