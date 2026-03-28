#include "main.h"
#include "usbd_core.h"
#include "usbd_desc.h"
#include "usbd_customhid.h"

void Error_Handler(void) { while (1) {} }

void SystemClock_Config(void);

static USBD_HandleTypeDef hdev;

static int8_t HID_Init(void)     { return 0; }
static int8_t HID_DeInit(void)   { return 0; }
static int8_t HID_OutEvent(uint8_t *buf) { (void)buf; return 0; }

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
    0xC0
};

static USBD_CUSTOM_HID_ItfTypeDef hid_fops = {
    hid_report_desc,
    HID_Init,
    HID_DeInit,
    HID_OutEvent,
};

int main(void) {
    HAL_Init();
    SystemClock_Config();

    __HAL_RCC_GPIOC_CLK_ENABLE();
    GPIO_InitTypeDef gpio = {GPIO_PIN_6, GPIO_MODE_OUTPUT_PP,
                             GPIO_NOPULL, GPIO_SPEED_FREQ_LOW};
    HAL_GPIO_Init(GPIOC, &gpio);

    USBD_Init(&hdev, &FS_Desc, DEVICE_FS);
    USBD_RegisterClass(&hdev, USBD_CUSTOM_HID_CLASS);
    USBD_CUSTOM_HID_RegisterInterface(&hdev, &hid_fops);
    USBD_Start(&hdev);

    while (1) {
        HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_6);
        HAL_Delay(500);
    }
}
