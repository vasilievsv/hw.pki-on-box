#pragma once

#include "board_config.h"

void SystemClock_Config(void);
void Error_Handler(void);
void Error_Handler_Ex(uint32_t code);

extern volatile uint32_t g_last_error;
