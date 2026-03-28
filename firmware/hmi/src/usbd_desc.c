#include "usbd_desc.h"
#include "usbd_core.h"
#include "usbd_conf.h"
#include <string.h>

#define USB_VID           0x0483U
#define USB_PID_HID_DFU   0x5750U   /* PKI-TRNG HID streamer */
#define USB_LANGID        0x0409U

static void str_to_unicode(const char *str, uint8_t *buf, uint16_t *len)
{
    uint8_t idx = 2U;
    while (*str && idx < 64U) {
        buf[idx++] = (uint8_t)*str++;
        buf[idx++] = 0U;
    }
    buf[0] = idx;
    buf[1] = USB_DESC_TYPE_STRING;
    *len   = idx;
}

static uint8_t g_str_buf[64];

__ALIGN_BEGIN static uint8_t dev_desc[USB_LEN_DEV_DESC] __ALIGN_END = {
    0x12, USB_DESC_TYPE_DEVICE,
    0x00, 0x02,                 /* bcdUSB 2.0 */
    0x00, 0x00, 0x00,           /* class/subclass/protocol */
    USB_MAX_EP0_SIZE,
    LOBYTE(USB_VID), HIBYTE(USB_VID),
    LOBYTE(USB_PID_HID_DFU), HIBYTE(USB_PID_HID_DFU),
    0x00, 0x02,                 /* bcdDevice */
    USBD_IDX_MFC_STR,
    USBD_IDX_PRODUCT_STR,
    USBD_IDX_SERIAL_STR,
    USBD_MAX_NUM_CONFIGURATION,
};

static uint8_t *get_dev_desc(USBD_SpeedTypeDef speed, uint16_t *len)
{
    (void)speed;
    *len = sizeof(dev_desc);
    return dev_desc;
}

static uint8_t *get_langid(USBD_SpeedTypeDef speed, uint16_t *len)
{
    (void)speed;
    static uint8_t buf[4] = { 4U, USB_DESC_TYPE_STRING,
                               LOBYTE(USB_LANGID), HIBYTE(USB_LANGID) };
    *len = 4U;
    return buf;
}

static uint8_t *get_mfr(USBD_SpeedTypeDef speed, uint16_t *len)
{
    (void)speed;
    str_to_unicode("PKI-on-Box", g_str_buf, len);
    return g_str_buf;
}

static uint8_t *get_product(USBD_SpeedTypeDef speed, uint16_t *len)
{
    (void)speed;
    str_to_unicode("PKI-TRNG", g_str_buf, len);
    return g_str_buf;
}

static uint8_t *get_serial(USBD_SpeedTypeDef speed, uint16_t *len)
{
    (void)speed;
    str_to_unicode("00000001", g_str_buf, len);
    return g_str_buf;
}

static uint8_t *get_config(USBD_SpeedTypeDef speed, uint16_t *len)
{
    (void)speed;
    str_to_unicode("DFU Config", g_str_buf, len);
    return g_str_buf;
}

static uint8_t *get_iface(USBD_SpeedTypeDef speed, uint16_t *len)
{
    (void)speed;
    str_to_unicode("DFU Interface", g_str_buf, len);
    return g_str_buf;
}

USBD_DescriptorsTypeDef FS_Desc = {
    get_dev_desc,
    get_langid,
    get_mfr,
    get_product,
    get_serial,
    get_config,
    get_iface,
};
