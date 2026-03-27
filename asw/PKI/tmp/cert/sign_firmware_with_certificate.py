def sign_firmware_with_certificate(firmware_data, private_key, certificate):
    """
    Подпись прошивки с включением информации о сертификате
    """
    # Хеширование прошивки
    digest = hashes.Hash(hashes.SHA256())
    digest.update(firmware_data)
    firmware_hash = digest.finalize()
    
    # Создание подписи
    signature = private_key.sign(firmware_data, ec.ECDSA(hashes.SHA256()))
    
    # Создание подписанного пакета
    signed_package = {
        'firmware': firmware_data,
        'signature': signature,
        'certificate': certificate.public_bytes(serialization.Encoding.PEM),
        'algorithm': 'ECDSA-P256-SHA256',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return signed_package

def create_firmware_image(signed_package):
    """
    Создание конечного образа прошивки
    """
    # Сериализация пакета (можно использовать CBOR, MessagePack, или простой бинарный формат)
    image = b"FIRMWARE_SIGNED_v1.0" + \
            len(signed_package['firmware']).to_bytes(4, 'big') + \
            signed_package['firmware'] + \
            len(signed_package['signature']).to_bytes(2, 'big') + \
            signed_package['signature'] + \
            len(signed_package['certificate']).to_bytes(4, 'big') + \
            signed_package['certificate']
    
    return image