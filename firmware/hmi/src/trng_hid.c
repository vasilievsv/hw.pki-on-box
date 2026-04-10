#include "trng_hid.h"
#include <string.h>

#define ERR_RCC_CLK     0x10
#define ERR_RNG_INIT    0x11
#define ERR_RNG_GEN     0x12
#define ERR_RNG_SECS    0x13
#define ERR_RNG_CECS    0x14
#define ERR_TSR1_STUCK  0x20
#define ERR_TSR1_EQUAL  0x21
#define ERR_TSR2_REP    0x30
#define ERR_TSR2_PROP   0x31

static RNG_HandleTypeDef hrng;
static uint32_t trng_prev = 0;
static uint8_t trng_rep_count = 0;
#define TRNG_REP_LIMIT 4

void TRNG_Init(void) {
    RCC_PeriphCLKInitTypeDef clk = {0};
    clk.PeriphClockSelection = RCC_PERIPHCLK_RNG;
#if defined(BSP_FAMILY_G4)
    clk.RngClockSelection    = RCC_RNGCLKSOURCE_HSI48;
#elif defined(BSP_FAMILY_H7)
    clk.RngClockSelection    = RCC_RNGCLKSOURCE_PLL;
#endif
    if (HAL_RCCEx_PeriphCLKConfig(&clk) != HAL_OK) Error_Handler_Ex(ERR_RCC_CLK);

    __HAL_RCC_RNG_CLK_ENABLE();
    hrng.Instance = RNG;
    if (HAL_RNG_Init(&hrng) != HAL_OK) Error_Handler_Ex(ERR_RNG_INIT);
}

void TRNG_StartupTest(void) {
    uint32_t v1, v2;
    if (HAL_RNG_GenerateRandomNumber(&hrng, &v1) != HAL_OK) Error_Handler_Ex(ERR_RNG_GEN);
    if (HAL_RNG_GenerateRandomNumber(&hrng, &v2) != HAL_OK) Error_Handler_Ex(ERR_RNG_GEN);
    if (v1 == 0x00000000U || v1 == 0xFFFFFFFFU) Error_Handler_Ex(ERR_TSR1_STUCK);
    if (v2 == 0x00000000U || v2 == 0xFFFFFFFFU) Error_Handler_Ex(ERR_TSR1_STUCK);
    if (v1 == v2) Error_Handler_Ex(ERR_TSR1_EQUAL);
    trng_prev = v2;
}

void TRNG_StatusCheck(void) {
    if (__HAL_RNG_GET_FLAG(&hrng, RNG_FLAG_SECS)) Error_Handler_Ex(ERR_RNG_SECS);
    if (__HAL_RNG_GET_FLAG(&hrng, RNG_FLAG_CECS)) Error_Handler_Ex(ERR_RNG_CECS);
}

void TRNG_FillReport(uint8_t *report, uint16_t len) {
    for (uint16_t i = 0; i < len; i += 4) {
        TRNG_StatusCheck();
        uint32_t rnd;
        if (HAL_RNG_GenerateRandomNumber(&hrng, &rnd) != HAL_OK)
            Error_Handler_Ex(ERR_RNG_GEN);
        if (rnd == trng_prev) Error_Handler_Ex(ERR_TSR2_REP);
        if ((rnd >> 24) == (trng_prev >> 24)) {
            trng_rep_count++;
            if (trng_rep_count >= TRNG_REP_LIMIT) Error_Handler_Ex(ERR_TSR2_PROP);
        } else {
            trng_rep_count = 0;
        }
        trng_prev = rnd;
        uint16_t copy = ((i + 4) <= len) ? 4 : (len - i);
        memcpy(&report[i], &rnd, copy);
    }
}