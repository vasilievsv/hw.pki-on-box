#include "usbd_customhid.h"
#include "usbd_ctlreq.h"

static uint8_t USBD_CUSTOM_HID_Init(USBD_HandleTypeDef *pdev, uint8_t cfgidx);
static uint8_t USBD_CUSTOM_HID_DeInit(USBD_HandleTypeDef *pdev, uint8_t cfgidx);
static uint8_t USBD_CUSTOM_HID_Setup(USBD_HandleTypeDef *pdev, USBD_SetupReqTypedef *req);
static uint8_t USBD_CUSTOM_HID_DataIn(USBD_HandleTypeDef *pdev, uint8_t epnum);
static uint8_t USBD_CUSTOM_HID_DataOut(USBD_HandleTypeDef *pdev, uint8_t epnum);
static uint8_t USBD_CUSTOM_HID_EP0_RxReady(USBD_HandleTypeDef *pdev);
static uint8_t *USBD_CUSTOM_HID_GetFSCfgDesc(uint16_t *length);
static uint8_t *USBD_CUSTOM_HID_GetHSCfgDesc(uint16_t *length);
static uint8_t *USBD_CUSTOM_HID_GetOtherSpeedCfgDesc(uint16_t *length);
static uint8_t *USBD_CUSTOM_HID_GetDeviceQualifierDesc(uint16_t *length);

USBD_ClassTypeDef USBD_CUSTOM_HID = {
    USBD_CUSTOM_HID_Init,
    USBD_CUSTOM_HID_DeInit,
    USBD_CUSTOM_HID_Setup,
    NULL,
    USBD_CUSTOM_HID_EP0_RxReady,
    USBD_CUSTOM_HID_DataIn,
    USBD_CUSTOM_HID_DataOut,
    NULL, NULL, NULL,
    USBD_CUSTOM_HID_GetHSCfgDesc,
    USBD_CUSTOM_HID_GetFSCfgDesc,
    USBD_CUSTOM_HID_GetOtherSpeedCfgDesc,
    USBD_CUSTOM_HID_GetDeviceQualifierDesc,
};

__ALIGN_BEGIN static uint8_t USBD_CUSTOM_HID_CfgDesc[USB_CUSTOM_HID_CONFIG_DESC_SIZ] __ALIGN_END = {
    0x09, USB_DESC_TYPE_CONFIGURATION, USB_CUSTOM_HID_CONFIG_DESC_SIZ, 0x00,
    0x01, 0x01, 0x00, 0x80, 0x32,
    /* Interface */
    0x09, USB_DESC_TYPE_INTERFACE, 0x00, 0x00, 0x02, 0x03, 0x00, 0x00, 0x00,
    /* HID descriptor */
    0x09, CUSTOM_HID_DESCRIPTOR_TYPE, 0x11, 0x01, 0x00, 0x01, 0x22,
    USBD_CUSTOM_HID_REPORT_DESC_SIZE, 0x00,
    /* EP1 IN */
    0x07, USB_DESC_TYPE_ENDPOINT, CUSTOM_HID_EPIN_ADDR, 0x03,
    CUSTOM_HID_EPIN_SIZE, 0x00, CUSTOM_HID_FS_BINTERVAL,
    /* EP1 OUT */
    0x07, USB_DESC_TYPE_ENDPOINT, CUSTOM_HID_EPOUT_ADDR, 0x03,
    CUSTOM_HID_EPOUT_SIZE, 0x00, CUSTOM_HID_FS_BINTERVAL,
};

__ALIGN_BEGIN static uint8_t USBD_CUSTOM_HID_Desc[USB_CUSTOM_HID_DESC_SIZ] __ALIGN_END = {
    0x09, CUSTOM_HID_DESCRIPTOR_TYPE, 0x11, 0x01, 0x00, 0x01, 0x22,
    USBD_CUSTOM_HID_REPORT_DESC_SIZE, 0x00,
};

__ALIGN_BEGIN static uint8_t USBD_CUSTOM_HID_DeviceQualifierDesc[USB_LEN_DEV_QUALIFIER_DESC] __ALIGN_END = {
    USB_LEN_DEV_QUALIFIER_DESC, USB_DESC_TYPE_DEVICE_QUALIFIER,
    0x00, 0x02, 0x00, 0x00, 0x00, 0x40, 0x01, 0x00,
};

static uint8_t USBD_CUSTOM_HID_Init(USBD_HandleTypeDef *pdev, uint8_t cfgidx)
{
    UNUSED(cfgidx);
    USBD_CUSTOM_HID_HandleTypeDef *hhid;

    hhid = USBD_malloc(sizeof(USBD_CUSTOM_HID_HandleTypeDef));
    if (hhid == NULL) { pdev->pClassData = NULL; return (uint8_t)USBD_EMEM; }

    pdev->pClassData = (void *)hhid;
    pdev->ep_in[CUSTOM_HID_EPIN_ADDR & 0xFU].bInterval  = CUSTOM_HID_FS_BINTERVAL;
    pdev->ep_out[CUSTOM_HID_EPOUT_ADDR & 0xFU].bInterval = CUSTOM_HID_FS_BINTERVAL;

    (void)USBD_LL_OpenEP(pdev, CUSTOM_HID_EPIN_ADDR,  USBD_EP_TYPE_INTR, CUSTOM_HID_EPIN_SIZE);
    pdev->ep_in[CUSTOM_HID_EPIN_ADDR & 0xFU].is_used = 1U;

    (void)USBD_LL_OpenEP(pdev, CUSTOM_HID_EPOUT_ADDR, USBD_EP_TYPE_INTR, CUSTOM_HID_EPOUT_SIZE);
    pdev->ep_out[CUSTOM_HID_EPOUT_ADDR & 0xFU].is_used = 1U;

    hhid->state = CUSTOM_HID_IDLE;
    ((USBD_CUSTOM_HID_ItfTypeDef *)pdev->pUserData)->Init();

    (void)USBD_LL_PrepareReceive(pdev, CUSTOM_HID_EPOUT_ADDR,
                                 hhid->Report_buf, USBD_CUSTOMHID_OUTREPORT_BUF_SIZE);
    return (uint8_t)USBD_OK;
}

static uint8_t USBD_CUSTOM_HID_DeInit(USBD_HandleTypeDef *pdev, uint8_t cfgidx)
{
    UNUSED(cfgidx);
    (void)USBD_LL_CloseEP(pdev, CUSTOM_HID_EPIN_ADDR);
    pdev->ep_in[CUSTOM_HID_EPIN_ADDR & 0xFU].is_used = 0U;
    (void)USBD_LL_CloseEP(pdev, CUSTOM_HID_EPOUT_ADDR);
    pdev->ep_out[CUSTOM_HID_EPOUT_ADDR & 0xFU].is_used = 0U;

    if (pdev->pClassData != NULL) {
        ((USBD_CUSTOM_HID_ItfTypeDef *)pdev->pUserData)->DeInit();
        USBD_free(pdev->pClassData);
        pdev->pClassData = NULL;
    }
    return (uint8_t)USBD_OK;
}

static uint8_t USBD_CUSTOM_HID_Setup(USBD_HandleTypeDef *pdev, USBD_SetupReqTypedef *req)
{
    USBD_CUSTOM_HID_HandleTypeDef *hhid = (USBD_CUSTOM_HID_HandleTypeDef *)pdev->pClassData;
    uint16_t len = 0U;
    uint8_t *pbuf = NULL;
    uint16_t status_info = 0U;
    USBD_StatusTypeDef ret = USBD_OK;

    if (hhid == NULL) { return (uint8_t)USBD_FAIL; }

    switch (req->bmRequest & USB_REQ_TYPE_MASK) {
        case USB_REQ_TYPE_CLASS:
            switch (req->bRequest) {
                case CUSTOM_HID_REQ_SET_PROTOCOL: hhid->Protocol  = (uint8_t)(req->wValue); break;
                case CUSTOM_HID_REQ_GET_PROTOCOL: (void)USBD_CtlSendData(pdev, (uint8_t *)&hhid->Protocol, 1U); break;
                case CUSTOM_HID_REQ_SET_IDLE:     hhid->IdleState = (uint8_t)(req->wValue >> 8U); break;
                case CUSTOM_HID_REQ_GET_IDLE:     (void)USBD_CtlSendData(pdev, (uint8_t *)&hhid->IdleState, 1U); break;
                case CUSTOM_HID_REQ_SET_REPORT:
                    hhid->IsReportAvailable = 1U;
                    (void)USBD_CtlPrepareRx(pdev, hhid->Report_buf, req->wLength);
                    break;
                default: USBD_CtlError(pdev, req); ret = USBD_FAIL; break;
            }
            break;

        case USB_REQ_TYPE_STANDARD:
            switch (req->bRequest) {
                case USB_REQ_GET_STATUS:
                    if (pdev->dev_state == USBD_STATE_CONFIGURED)
                        (void)USBD_CtlSendData(pdev, (uint8_t *)&status_info, 2U);
                    else { USBD_CtlError(pdev, req); ret = USBD_FAIL; }
                    break;
                case USB_REQ_GET_DESCRIPTOR:
                    if ((req->wValue >> 8U) == CUSTOM_HID_REPORT_DESC) {
                        len  = MIN(USBD_CUSTOM_HID_REPORT_DESC_SIZE, req->wLength);
                        pbuf = ((USBD_CUSTOM_HID_ItfTypeDef *)pdev->pUserData)->pReport;
                    } else if ((req->wValue >> 8U) == CUSTOM_HID_DESCRIPTOR_TYPE) {
                        pbuf = USBD_CUSTOM_HID_Desc;
                        len  = MIN(USB_CUSTOM_HID_DESC_SIZ, req->wLength);
                    }
                    (void)USBD_CtlSendData(pdev, pbuf, len);
                    break;
                case USB_REQ_GET_INTERFACE:
                    if (pdev->dev_state == USBD_STATE_CONFIGURED)
                        (void)USBD_CtlSendData(pdev, (uint8_t *)&hhid->AltSetting, 1U);
                    else { USBD_CtlError(pdev, req); ret = USBD_FAIL; }
                    break;
                case USB_REQ_SET_INTERFACE:
                    if (pdev->dev_state == USBD_STATE_CONFIGURED)
                        hhid->AltSetting = (uint8_t)(req->wValue);
                    else { USBD_CtlError(pdev, req); ret = USBD_FAIL; }
                    break;
                case USB_REQ_CLEAR_FEATURE: break;
                default: USBD_CtlError(pdev, req); ret = USBD_FAIL; break;
            }
            break;

        default: USBD_CtlError(pdev, req); ret = USBD_FAIL; break;
    }
    return (uint8_t)ret;
}

uint8_t USBD_CUSTOM_HID_SendReport(USBD_HandleTypeDef *pdev, uint8_t *report, uint16_t len)
{
    USBD_CUSTOM_HID_HandleTypeDef *hhid;
    if (pdev->pClassData == NULL) { return (uint8_t)USBD_FAIL; }
    hhid = (USBD_CUSTOM_HID_HandleTypeDef *)pdev->pClassData;
    if (pdev->dev_state == USBD_STATE_CONFIGURED) {
        if (hhid->state == CUSTOM_HID_IDLE) {
            hhid->state = CUSTOM_HID_BUSY;
            (void)USBD_LL_Transmit(pdev, CUSTOM_HID_EPIN_ADDR, report, len);
        } else { return (uint8_t)USBD_BUSY; }
    }
    return (uint8_t)USBD_OK;
}

static uint8_t USBD_CUSTOM_HID_DataIn(USBD_HandleTypeDef *pdev, uint8_t epnum)
{
    UNUSED(epnum);
    ((USBD_CUSTOM_HID_HandleTypeDef *)pdev->pClassData)->state = CUSTOM_HID_IDLE;
    return (uint8_t)USBD_OK;
}

static uint8_t USBD_CUSTOM_HID_DataOut(USBD_HandleTypeDef *pdev, uint8_t epnum)
{
    UNUSED(epnum);
    USBD_CUSTOM_HID_HandleTypeDef *hhid;
    if (pdev->pClassData == NULL) { return (uint8_t)USBD_FAIL; }
    hhid = (USBD_CUSTOM_HID_HandleTypeDef *)pdev->pClassData;
    ((USBD_CUSTOM_HID_ItfTypeDef *)pdev->pUserData)->OutEvent(hhid->Report_buf);
    (void)USBD_LL_PrepareReceive(pdev, CUSTOM_HID_EPOUT_ADDR,
                                 hhid->Report_buf, USBD_CUSTOMHID_OUTREPORT_BUF_SIZE);
    return (uint8_t)USBD_OK;
}

uint8_t USBD_CUSTOM_HID_ReceivePacket(USBD_HandleTypeDef *pdev)
{
    USBD_CUSTOM_HID_HandleTypeDef *hhid;
    if (pdev->pClassData == NULL) { return (uint8_t)USBD_FAIL; }
    hhid = (USBD_CUSTOM_HID_HandleTypeDef *)pdev->pClassData;
    (void)USBD_LL_PrepareReceive(pdev, CUSTOM_HID_EPOUT_ADDR,
                                 hhid->Report_buf, USBD_CUSTOMHID_OUTREPORT_BUF_SIZE);
    return (uint8_t)USBD_OK;
}

static uint8_t USBD_CUSTOM_HID_EP0_RxReady(USBD_HandleTypeDef *pdev)
{
    USBD_CUSTOM_HID_HandleTypeDef *hhid = (USBD_CUSTOM_HID_HandleTypeDef *)pdev->pClassData;
    if (hhid == NULL) { return (uint8_t)USBD_FAIL; }
    if (hhid->IsReportAvailable == 1U) {
        ((USBD_CUSTOM_HID_ItfTypeDef *)pdev->pUserData)->OutEvent(hhid->Report_buf);
        hhid->IsReportAvailable = 0U;
    }
    return (uint8_t)USBD_OK;
}

static uint8_t *USBD_CUSTOM_HID_GetFSCfgDesc(uint16_t *length)
{
    *length = (uint16_t)sizeof(USBD_CUSTOM_HID_CfgDesc);
    return USBD_CUSTOM_HID_CfgDesc;
}

static uint8_t *USBD_CUSTOM_HID_GetHSCfgDesc(uint16_t *length)
{
    *length = (uint16_t)sizeof(USBD_CUSTOM_HID_CfgDesc);
    return USBD_CUSTOM_HID_CfgDesc;
}

static uint8_t *USBD_CUSTOM_HID_GetOtherSpeedCfgDesc(uint16_t *length)
{
    *length = (uint16_t)sizeof(USBD_CUSTOM_HID_CfgDesc);
    return USBD_CUSTOM_HID_CfgDesc;
}

static uint8_t *USBD_CUSTOM_HID_GetDeviceQualifierDesc(uint16_t *length)
{
    *length = (uint16_t)sizeof(USBD_CUSTOM_HID_DeviceQualifierDesc);
    return USBD_CUSTOM_HID_DeviceQualifierDesc;
}

uint8_t USBD_CUSTOM_HID_RegisterInterface(USBD_HandleTypeDef *pdev,
                                          USBD_CUSTOM_HID_ItfTypeDef *fops)
{
    if (fops == NULL) { return (uint8_t)USBD_FAIL; }
    pdev->pUserData = fops;
    return (uint8_t)USBD_OK;
}
