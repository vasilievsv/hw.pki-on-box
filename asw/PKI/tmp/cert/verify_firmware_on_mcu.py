def verify_firmware_on_mcu(firmware_image):
    """
    Верификация прошивки на стороне MCU
    """
    # Парсинг образа
    header = firmware_image[:18]  # "FIRMWARE_SIGNED_v1.0"
    if header != b"FIRMWARE_SIGNED_v1.0":
        return False
    
    offset = 18
    firmware_len = int.from_bytes(firmware_image[offset:offset+4], 'big')
    offset += 4
    firmware = firmware_image[offset:offset+firmware_len]
    offset += firmware_len
    
    signature_len = int.from_bytes(firmware_image[offset:offset+2], 'big')
    offset += 2
    signature = firmware_image[offset:offset+signature_len]
    offset += signature_len
    
    cert_len = int.from_bytes(firmware_image[offset:offset+4], 'big')
    offset += 4
    certificate_data = firmware_image[offset:offset+cert_len]
    
    # Загрузка корневого сертификата (предустановлен в MCU)
    root_certificate = load_root_certificate()  # Из защищенной памяти
    
    # Верификация цепочки сертификатов
    if not verify_certificate_chain(certificate_data, root_certificate):
        return False
    
    # Извлечение публичного ключа из сертификата
    public_key = extract_public_key_from_certificate(certificate_data)
    
    # Верификация подписи
    return verify_signature(firmware, signature, public_key)