# first_ceremony.py
def perform_first_root_ca_ceremony():
    """Выполнение первой церемонии выпуска Master Root CA"""
    
    print("🎭 ПЕРВАЯ ЦЕРЕМОНИЯ ВЫПУСКА MASTER ROOT CA")
    print("=" * 60)
    
    # Участники церемонии
    participants = [
        "Главный криптограф",
        "Специалист по безопасности", 
        "Аудитор",
        "Технический администратор"
    ]
    
    # Инициализация церемонии
    ceremony = RootCAIssuanceCeremony(
        ceremony_id="FIRST_ROOT_CA_2024",
        participants=participants
    )
    
    # Инициализация хранилища
    storage = RootCAFileSystemStorage("./master_root_ca")
    
    try:
        # Выполнение церемонии
        ceremony.perform_ceremony()
        
        # Сохранение результатов
        storage.store_master_root_ca(
            ceremony.master_private_key,
            ceremony.master_certificate,
            ceremony.ceremony_id
        )
        
        # Статус хранилища
        status = storage.get_storage_status()
        print("\n📊 СТАТУС ХРАНИЛИЩА:")
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        # Экспорт публичного сертификата
        storage.export_public_certificate("PEM")
        
        print("\n✅ ЦЕРЕМОНИЯ УСПЕШНО ЗАВЕРШЕНА!")
        print("   Master Root CA готов к использованию")
        
    except Exception as e:
        print(f"❌ Церемония прервана с ошибкой: {e}")
        # В реальной системе здесь должна быть процедура аварийного завершения

if __name__ == "__main__":
    perform_first_root_ca_ceremony()