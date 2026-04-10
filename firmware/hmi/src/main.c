#include "main.h"
#include "usbd_core.h"
#include "usbd_desc.h"
#include "usbd_customhid.h"
#include "trng_hid.h"

static IWDG_HandleTypeDef hiwdg;

void Error_Handler(void) {                                           /* G3 */
    __disable_irq();
    while (1) {
        HAL_GPIO_TogglePin(BSP_LED_PORT, BSP_LED_PIN);
        for (volatile uint32_t i = 0; i < 100000; i++);
    }
}

void SystemClock_Config(void);

static USBD_HandleTypeDef hdev;

static int8_t HID_Init(void)            { return 0; }
static int8_t HID_DeInit(void)          { return 0; }
static int8_t HID_OutEvent(uint8_t *buf){ (void)buf; return 0; }

static uint8_t hid_report_desc[] = {
    0x06, 0x00, 0xFF,
    0x09, 0x01,
    0xA1, 0x01,
    0x09, 0x01,
    0x15, 0x00,
    0x26, 0xFF, 0x00,
    0x75, 0x08,
    0x95, 0x40,
    0x81, 0x02,
    0x09, 0x02,
    0x15, 0x00,
    0x26, 0xFF, 0x00,
    0x75, 0x08,
    0x95, 0x40,
    0x91, 0x02,
    0xC0
};

static USBD_CUSTOM_HID_ItfTypeDef hid_fops = {
    hid_report_desc,
    HID_Init,
    HID_DeInit,
    HID_OutEvent,
};

static void IWDG_Init(void) {                                       /* G5 */
#if defined(BSP_FAMILY_H7)
    hiwdg.Instance       = IWDG1;
#else
    hiwdg.Instance       = IWDG;
#endif
    hiwdg.Init.Prescaler = IWDG_PRESCALER_64;
    hiwdg.Init.Window    = IWDG_WINDOW_DISABLE;
    hiwdg.Init.Reload    = 1000;
    if (HAL_IWDG_Init(&hiwdg) != HAL_OK) Error_Handler();
}

int main(void) {
    HAL_Init();
    SystemClock_Config();

    BSP_LED_CLK_EN();
    GPIO_InitTypeDef gpio = {BSP_LED_PIN, GPIO_MODE_OUTPUT_PP,
                             GPIO_NOPULL, GPIO_SPEED_FREQ_LOW};
    HAL_GPIO_Init(BSP_LED_PORT, &gpio);

    TRNG_Init();
    TRNG_StartupTest();                                              /* G4: TSR-1 */
    IWDG_Init();                                                     /* G5: watchdog */

    USBD_Init(&hdev, &FS_Desc, DEVICE_FS);
    USBD_RegisterClass(&hdev, USBD_CUSTOM_HID_CLASS);
    USBD_CUSTOM_HID_RegisterInterface(&hdev, &hid_fops);
    USBD_Start(&hdev);

    uint8_t report[64];
    uint32_t last_blink = 0;

    while (1) {
        HAL_IWDG_Refresh(&hiwdg);                                   /* G5: refresh */

        if (hdev.pClassData != NULL) {
            TRNG_FillReport(report, sizeof(report));
            uint8_t res = USBD_CUSTOM_HID_SendReport(&hdev, report, sizeof(report));
            if (res != USBD_OK) {
                HAL_Delay(1);                                        /* G9: rate limiting */
            }
        }

        uint32_t now = HAL_GetTick();
        uint32_t interval = (hdev.pClassData != NULL) ? 100 : 500;
        if (now - last_blink >= interval) {
            HAL_GPIO_TogglePin(BSP_LED_PORT, BSP_LED_PIN);
            last_blink = now;
        }
    }
}
