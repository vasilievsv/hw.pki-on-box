#ifndef USBD_CONF_H
#define USBD_CONF_H

#include "board_config.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define USBD_MAX_NUM_INTERFACES      1U
#define USBD_MAX_NUM_CONFIGURATION   1U
#define USBD_MAX_STR_DESC_SIZ        512U
#define USBD_SELF_POWERED            1U
#define USBD_DEBUG_LEVEL             0U

/* DFU transfer size — must match USBD_DFU_XFER_SIZE */
#define USBD_DFU_XFER_SIZE           1024U
#define USBD_DFU_APP_DEFAULT_ADD     0x0800C000U

#define USBD_malloc         USBD_static_malloc
#define USBD_free           USBD_static_free
#define USBD_memset         memset
#define USBD_memcpy         memcpy
#define USBD_Delay          HAL_Delay

#define USBD_UseCoreId      0U

#if (USBD_DEBUG_LEVEL > 0U)
#define USBD_UsrLog(...)    printf(__VA_ARGS__)
#else
#define USBD_UsrLog(...)
#endif
#define USBD_ErrLog(...)
#define USBD_DbgLog(...)

void *USBD_static_malloc(uint32_t size);
void  USBD_static_free(void *p);

#endif /* USBD_CONF_H */
