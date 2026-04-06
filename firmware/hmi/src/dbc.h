#pragma once
/**
 * dbc.h — Design by Contract macros for embedded C (STM32).
 *
 * Source: trng_hid.contract.yaml
 * Pattern: state-machine.com / Barr Group DbC for embedded
 *
 * Usage:
 *   DBC_REQUIRE(ptr != NULL);
 *   DBC_ENSURE(result == HAL_OK);
 *   DBC_INVARIANT(hrng.Instance == RNG);
 *
 * In production (NDEBUG defined): macros compile to nothing.
 * In debug: triggers DBC_Fault_Handler with file/line info.
 */

#ifdef NDEBUG

#define DBC_REQUIRE(expr)    ((void)0)
#define DBC_ENSURE(expr)     ((void)0)
#define DBC_INVARIANT(expr)  ((void)0)

#else

#define DBC_REQUIRE(expr) \
    do { if (!(expr)) DBC_Fault_Handler(__FILE__, __LINE__, "REQUIRE: " #expr); } while(0)

#define DBC_ENSURE(expr) \
    do { if (!(expr)) DBC_Fault_Handler(__FILE__, __LINE__, "ENSURE: " #expr); } while(0)

#define DBC_INVARIANT(expr) \
    do { if (!(expr)) DBC_Fault_Handler(__FILE__, __LINE__, "INVARIANT: " #expr); } while(0)

void DBC_Fault_Handler(const char *file, int line, const char *expr);

#endif
