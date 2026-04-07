#include "trng_hid.h"
#include <string.h>

static RNG_HandleTypeDef hrng;
static uint32_t trng_prev = 0;

void TRNG_Init(void) {
    RCC_PeriphCLKInitTypeDef clk = {0};
    clk.PeriphClockSelection = RCC_PERIPHCLK_RNG;
#if defined(BSP_FAMILY_G4)
    clk.RngClockSelection    = RCC_RNGCLKSOURCE_HSI48;
#elif defined(BSP_FAMILY_H7)
    clk.RngClockSelection    = RCC_RNGCLKSOURCE_PLL;
#endif
    if (HAL_RCCEx_PeriphCLKConfig(&clk) != HAL_OK) Error_Handler(); /* G7 */

    __HAL_RCC_RNG_CLK_ENABLE();
    hrng.Instance = RNG;
    if (HAL_RNG_Init(&hrng) != HAL_OK) Error_Handler();             /* G8 */
}

void TRNG_StartupTest(void) {                                       /* G4: TSR-1 */
    uint32_t val;
    if (HAL_RNG_GenerateRandomNumber(&hrng, &val) != HAL_OK) Error_Handler();
    if (val == 0x00000000U || val == 0xFFFFFFFFU) Error_Handler();
    trng_prev = val;
}

void TRNG_StatusCheck(void) {                                        /* G2: SECS/CECS */
    if (__HAL_RNG_GET_FLAG(&hrng, RNG_FLAG_SECS)) Error_Handler();
    if (__HAL_RNG_GET_FLAG(&hrng, RNG_FLAG_CECS)) Error_Handler();
}

void TRNG_FillReport(uint8_t *report, uint16_t len) {
    report[0] = 0x01;                                                /* G10: Report ID */
    for (uint16_t i = 1; i < len; i += 4) {
        TRNG_StatusCheck();                                          /* G2: перед каждым чтением */
        uint32_t rnd;
        if (HAL_RNG_GenerateRandomNumber(&hrng, &rnd) != HAL_OK)    /* G1 */
            Error_Handler();
        if (rnd == trng_prev) Error_Handler();                       /* G6: TSR-2 continuous */
        trng_prev = rnd;
        uint16_t copy = ((i + 4) <= len) ? 4 : (len - i);
        memcpy(&report[i], &rnd, copy);
    }
}
