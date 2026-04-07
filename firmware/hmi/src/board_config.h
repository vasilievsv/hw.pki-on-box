#pragma once

#if defined(STM32G4xx) || defined(STM32G474xx) || defined(STM32G431xx)
  #include "stm32g4xx_hal.h"
  #define BSP_LED_PORT        GPIOC
  #define BSP_LED_PIN         GPIO_PIN_6
  #define BSP_LED_CLK_EN()    __HAL_RCC_GPIOC_CLK_ENABLE()
  #define BSP_RNG_CLK_SRC     RCC_RNGCLKSOURCE_HSI48
  #define BSP_FAMILY_G4       1

#elif defined(STM32H7xx) || defined(STM32H750xx)
  #include "stm32h7xx_hal.h"
  #define BSP_LED_PORT        GPIOE
  #define BSP_LED_PIN         GPIO_PIN_3
  #define BSP_LED_CLK_EN()    __HAL_RCC_GPIOE_CLK_ENABLE()
  #define BSP_RNG_CLK_SRC     RCC_RNGCLKSOURCE_PLL
  #define BSP_FAMILY_H7       1

#else
  #error "Unsupported MCU family — define STM32G4xx or STM32H7xx"
#endif
