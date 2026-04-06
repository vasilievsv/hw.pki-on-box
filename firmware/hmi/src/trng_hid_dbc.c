/**
 * trng_hid_dbc.c — TRNG HID с DBC-аннотациями из trng_hid.contract.yaml.
 *
 * Это ЭТАЛОННАЯ реализация. Текущий trng_hid.c — минимальная (без проверок).
 * Разница = drift (см. drift_check_firmware.py L1).
 *
 * Contract phases covered:
 *   trng_init, startup_test, rng_status_check, fill_report
 */
#include "trng_hid.h"
#include "dbc.h"
#include <string.h>

static RNG_HandleTypeDef hrng;
static uint32_t trng_prev = 0;
static uint8_t trng_initialized = 0;

/* ── phase: trng_init ─────────────────────────────────────── */

static void TRNG_CheckRngStatus(void) {
    /* contract phase: rng_status_check
     * postcondition: RNG_SR.SECS == 0 && RNG_SR.CECS == 0 */
    DBC_INVARIANT(!__HAL_RNG_GET_FLAG(&hrng, RNG_FLAG_SECS));
    DBC_INVARIANT(!__HAL_RNG_GET_FLAG(&hrng, RNG_FLAG_CECS));
}

static void TRNG_StartupTest(void) {
    /* contract phase: startup_test (TSR-1, NIST 800-90B §4.3)
     * postcondition: val != 0x00000000 && val != 0xFFFFFFFF */
    uint32_t val;
    HAL_StatusTypeDef st = HAL_RNG_GenerateRandomNumber(&hrng, &val);
    DBC_ENSURE(st == HAL_OK);
    DBC_ENSURE(val != 0x00000000U);
    DBC_ENSURE(val != 0xFFFFFFFFU);
    trng_prev = val;
}

void TRNG_Init(void) {
    /* contract phase: trng_init
     * precondition: SystemClock_Config done, HSI48 active */
    RCC_PeriphCLKInitTypeDef clk = {0};
    clk.PeriphClockSelection = RCC_PERIPHCLK_RNG;
    clk.RngClockSelection    = RCC_RNGCLKSOURCE_HSI48;

    HAL_StatusTypeDef st;

    st = HAL_RCCEx_PeriphCLKConfig(&clk);
    DBC_ENSURE(st == HAL_OK);  /* G7 fix */

    __HAL_RCC_RNG_CLK_ENABLE();
    hrng.Instance = RNG;

    st = HAL_RNG_Init(&hrng);
    DBC_ENSURE(st == HAL_OK);  /* G8 fix */

    DBC_INVARIANT(hrng.Instance == RNG);

    TRNG_CheckRngStatus();     /* G2 fix */
    TRNG_StartupTest();        /* G4 fix */

    trng_initialized = 1;
}

/* ── phase: fill_report ───────────────────────────────────── */

void TRNG_FillReport(uint8_t *report, uint16_t len) {
    /* contract phase: fill_report
     * precondition: trng_init done, report != NULL, len > 0 && len <= 64 */
    DBC_REQUIRE(trng_initialized == 1);
    DBC_REQUIRE(report != NULL);
    DBC_REQUIRE(len > 0 && len <= 64);

    report[0] = 0x01;  /* G10 fix: HID Report ID */

    for (uint16_t i = 1; i < len; i += 4) {
        TRNG_CheckRngStatus();  /* G2: check before each read */

        uint32_t rnd;
        HAL_StatusTypeDef st = HAL_RNG_GenerateRandomNumber(&hrng, &rnd);
        DBC_ENSURE(st == HAL_OK);  /* G1 fix */

        /* TSR-2: continuous health check (G6 fix) */
        DBC_ENSURE(rnd != trng_prev);
        trng_prev = rnd;

        uint16_t copy = ((i + 4) <= len) ? 4 : (len - i);
        memcpy(&report[i], &rnd, copy);
    }

    /* postcondition: report filled */
    DBC_ENSURE(report[0] == 0x01);
}

/* ── DBC fault handler ────────────────────────────────────── */

#ifndef NDEBUG
void DBC_Fault_Handler(const char *file, int line, const char *expr) {
    (void)file;
    (void)line;
    (void)expr;
    /* In debug: breakpoint here. In production: NDEBUG → macros removed. */
    __disable_irq();
    while (1) {
        /* LED rapid blink for visual indication */
    }
}
#endif
