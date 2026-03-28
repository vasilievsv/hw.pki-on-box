#include "usbd_conf.h"
#include "usbd_core.h"
#include "usbd_customhid.h"

static PCD_HandleTypeDef hpcd_USB_FS;

/* ── HAL PCD MSP ──────────────────────────────────────────────────────────── */

void HAL_PCD_MspInit(PCD_HandleTypeDef *pcdHandle)
{
    if (pcdHandle->Instance == USB) {
        RCC->CRRCR |= RCC_CRRCR_HSI48ON;
        while (!(RCC->CRRCR & RCC_CRRCR_HSI48RDY)) {}
        RCC->CCIPR &= ~RCC_CCIPR_CLK48SEL;
        __HAL_RCC_USB_CLK_ENABLE();
        HAL_NVIC_SetPriority(USB_LP_IRQn, 5U, 0U);
        /* IRQ включается после USBD_Start — не здесь */
    }
}

void HAL_PCD_MspDeInit(PCD_HandleTypeDef *pcdHandle)
{
    if (pcdHandle->Instance == USB) {
        __HAL_RCC_USB_CLK_DISABLE();
        HAL_NVIC_DisableIRQ(USB_LP_IRQn);
    }
}

/* ── USB IRQ ──────────────────────────────────────────────────────────────── */

void USB_LP_IRQHandler(void)
{
    HAL_PCD_IRQHandler(&hpcd_USB_FS);
}

/* ── HAL PCD callbacks → USBD Core ───────────────────────────────────────── */

void HAL_PCD_SetupStageCallback(PCD_HandleTypeDef *hpcd)
{
    USBD_LL_SetupStage((USBD_HandleTypeDef *)hpcd->pData, (uint8_t *)hpcd->Setup);
}

void HAL_PCD_DataOutStageCallback(PCD_HandleTypeDef *hpcd, uint8_t epnum)
{
    USBD_LL_DataOutStage((USBD_HandleTypeDef *)hpcd->pData, epnum,
                         hpcd->OUT_ep[epnum].xfer_buff);
}

void HAL_PCD_DataInStageCallback(PCD_HandleTypeDef *hpcd, uint8_t epnum)
{
    USBD_LL_DataInStage((USBD_HandleTypeDef *)hpcd->pData, epnum,
                        hpcd->IN_ep[epnum].xfer_buff);
}

void HAL_PCD_SOFCallback(PCD_HandleTypeDef *hpcd)
{
    USBD_LL_SOF((USBD_HandleTypeDef *)hpcd->pData);
}

void HAL_PCD_ResetCallback(PCD_HandleTypeDef *hpcd)
{
    USBD_LL_SetSpeed((USBD_HandleTypeDef *)hpcd->pData, USBD_SPEED_FULL);
    USBD_LL_Reset((USBD_HandleTypeDef *)hpcd->pData);
}

void HAL_PCD_SuspendCallback(PCD_HandleTypeDef *hpcd)
{
    USBD_LL_Suspend((USBD_HandleTypeDef *)hpcd->pData);
}

void HAL_PCD_ResumeCallback(PCD_HandleTypeDef *hpcd)
{
    USBD_LL_Resume((USBD_HandleTypeDef *)hpcd->pData);
}

void HAL_PCD_ConnectCallback(PCD_HandleTypeDef *hpcd)
{
    USBD_LL_DevConnected((USBD_HandleTypeDef *)hpcd->pData);
}

void HAL_PCD_DisconnectCallback(PCD_HandleTypeDef *hpcd)
{
    USBD_LL_DevDisconnected((USBD_HandleTypeDef *)hpcd->pData);
}

/* ── USBD LL API ──────────────────────────────────────────────────────────── */

USBD_StatusTypeDef USBD_LL_Init(USBD_HandleTypeDef *pdev)
{
    hpcd_USB_FS.Instance                     = USB;
    hpcd_USB_FS.Init.dev_endpoints           = 8U;
    hpcd_USB_FS.Init.speed                   = PCD_SPEED_FULL;
    hpcd_USB_FS.Init.phy_itface              = PCD_PHY_EMBEDDED;
    hpcd_USB_FS.Init.Sof_enable              = DISABLE;
    hpcd_USB_FS.Init.low_power_enable        = DISABLE;
    hpcd_USB_FS.Init.lpm_enable              = DISABLE;
    hpcd_USB_FS.Init.battery_charging_enable = DISABLE;

    if (HAL_PCD_Init(&hpcd_USB_FS) != HAL_OK) { return USBD_FAIL; }

    /* PMA layout: EP0 IN/OUT + EP1 IN/OUT (HID 64-byte) */
    HAL_PCDEx_PMAConfig(&hpcd_USB_FS, 0x00U, PCD_SNG_BUF, 0x18U);
    HAL_PCDEx_PMAConfig(&hpcd_USB_FS, 0x80U, PCD_SNG_BUF, 0x58U);
    HAL_PCDEx_PMAConfig(&hpcd_USB_FS, 0x81U, PCD_SNG_BUF, 0x98U);
    HAL_PCDEx_PMAConfig(&hpcd_USB_FS, 0x01U, PCD_SNG_BUF, 0xD8U);

    hpcd_USB_FS.pData = pdev;
    pdev->pData       = &hpcd_USB_FS;
    return USBD_OK;
}

USBD_StatusTypeDef USBD_LL_DeInit(USBD_HandleTypeDef *pdev)
{
    HAL_PCD_DeInit((PCD_HandleTypeDef *)pdev->pData);
    return USBD_OK;
}

USBD_StatusTypeDef USBD_LL_Start(USBD_HandleTypeDef *pdev)
{
    HAL_NVIC_EnableIRQ(USB_LP_IRQn);  /* включаем только после полной init */
    HAL_PCD_Start((PCD_HandleTypeDef *)pdev->pData);
    return USBD_OK;
}

USBD_StatusTypeDef USBD_LL_Stop(USBD_HandleTypeDef *pdev)
{
    HAL_PCD_Stop((PCD_HandleTypeDef *)pdev->pData);
    return USBD_OK;
}

USBD_StatusTypeDef USBD_LL_OpenEP(USBD_HandleTypeDef *pdev, uint8_t ep_addr,
                                   uint8_t ep_type, uint16_t ep_mps)
{
    HAL_PCD_EP_Open((PCD_HandleTypeDef *)pdev->pData, ep_addr, ep_mps, ep_type);
    return USBD_OK;
}

USBD_StatusTypeDef USBD_LL_CloseEP(USBD_HandleTypeDef *pdev, uint8_t ep_addr)
{
    HAL_PCD_EP_Close((PCD_HandleTypeDef *)pdev->pData, ep_addr);
    return USBD_OK;
}

USBD_StatusTypeDef USBD_LL_FlushEP(USBD_HandleTypeDef *pdev, uint8_t ep_addr)
{
    HAL_PCD_EP_Flush((PCD_HandleTypeDef *)pdev->pData, ep_addr);
    return USBD_OK;
}

USBD_StatusTypeDef USBD_LL_StallEP(USBD_HandleTypeDef *pdev, uint8_t ep_addr)
{
    HAL_PCD_EP_SetStall((PCD_HandleTypeDef *)pdev->pData, ep_addr);
    return USBD_OK;
}

USBD_StatusTypeDef USBD_LL_ClearStallEP(USBD_HandleTypeDef *pdev, uint8_t ep_addr)
{
    HAL_PCD_EP_ClrStall((PCD_HandleTypeDef *)pdev->pData, ep_addr);
    return USBD_OK;
}

uint8_t USBD_LL_IsStallEP(USBD_HandleTypeDef *pdev, uint8_t ep_addr)
{
    PCD_HandleTypeDef *hpcd = (PCD_HandleTypeDef *)pdev->pData;
    if ((ep_addr >> 7U) & 0x01U)
        return hpcd->IN_ep[ep_addr & 0x7FU].is_stall;
    return hpcd->OUT_ep[ep_addr & 0x7FU].is_stall;
}

USBD_StatusTypeDef USBD_LL_SetUSBAddress(USBD_HandleTypeDef *pdev, uint8_t dev_addr)
{
    HAL_PCD_SetAddress((PCD_HandleTypeDef *)pdev->pData, dev_addr);
    return USBD_OK;
}

USBD_StatusTypeDef USBD_LL_Transmit(USBD_HandleTypeDef *pdev, uint8_t ep_addr,
                                     uint8_t *pbuf, uint32_t size)
{
    HAL_PCD_EP_Transmit((PCD_HandleTypeDef *)pdev->pData, ep_addr, pbuf, size);
    return USBD_OK;
}

USBD_StatusTypeDef USBD_LL_PrepareReceive(USBD_HandleTypeDef *pdev, uint8_t ep_addr,
                                           uint8_t *pbuf, uint32_t size)
{
    HAL_PCD_EP_Receive((PCD_HandleTypeDef *)pdev->pData, ep_addr, pbuf, size);
    return USBD_OK;
}

uint32_t USBD_LL_GetRxDataSize(USBD_HandleTypeDef *pdev, uint8_t ep_addr)
{
    return HAL_PCD_EP_GetRxCount((PCD_HandleTypeDef *)pdev->pData, ep_addr);
}

void USBD_LL_Delay(uint32_t Delay) { HAL_Delay(Delay); }

/* Static allocator — Custom HID handle */
void *USBD_static_malloc(uint32_t size)
{
    (void)size;
    static uint32_t mem[sizeof(USBD_CUSTOM_HID_HandleTypeDef) / 4U + 1U];
    return mem;
}

void USBD_static_free(void *p) { (void)p; }
