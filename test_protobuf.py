#!/usr/bin/env python3
"""
Test específico para verificar importación de Protobuf
"""
import sys
import os
sys.path.insert(0, '/home/keith/coding/entrega-4-5/src')
sys.path.insert(0, '/home/keith/coding/entrega-4-5')

def test_protobuf_import():
    """Test de importación de clases Protobuf"""
    print("🔍 Testando importación de Protobuf...")
    
    try:
        # Añadir directorio generated al path
        generated_dir = '/home/keith/coding/entrega-4-5/generated'
        sys.path.insert(0, generated_dir)
        
        # Importar todas las clases
        import common_pb2
        import tracking_pb2
        import campaign_pb2
        import partner_pb2
        import collector_pb2
        from google.protobuf.timestamp_pb2 import Timestamp
        
        print("✅ Todas las clases Protobuf importadas correctamente")
        
        # Crear instancia de prueba
        meta = common_pb2.Meta()
        meta.event_id = "test-123"
        meta.correlation_id = "corr-456"
        
        print(f"✅ Meta creado: event_id={meta.event_id}")
        
        # Crear comando de click
        cmd = tracking_pb2.RegisterClickCommand()
        cmd.command_id = "cmd-test-789"
        cmd.click_id = "click-abc"
        cmd.campaign_id = "camp-def"
        cmd.partner_id = "partner-ghi"
        
        print(f"✅ RegisterClickCommand creado: click_id={cmd.click_id}")
        
        # Serializar y deserializar
        data = cmd.SerializeToString()
        cmd2 = tracking_pb2.RegisterClickCommand()
        cmd2.ParseFromString(data)
        
        print(f"✅ Serialización exitosa: {len(data)} bytes")
        print(f"✅ Deserialización exitosa: click_id={cmd2.click_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test de Protobuf: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_event_collector_protobuf():
    """Test de importación en Event Collector"""
    print("\n🔍 Testando Protobuf en Event Collector...")
    
    try:
        from aeropartners.event_collector.pulsar_client import PulsarProducer, PROTOBUF_AVAILABLE
        
        print(f"✅ PulsarProducer importado correctamente")
        print(f"✅ PROTOBUF_AVAILABLE = {PROTOBUF_AVAILABLE}")
        
        if PROTOBUF_AVAILABLE:
            print("✅ Las clases Protobuf están disponibles en Event Collector")
        else:
            print("❌ Las clases Protobuf NO están disponibles en Event Collector")
            
        return PROTOBUF_AVAILABLE
        
    except Exception as e:
        print(f"❌ Error importando Event Collector: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Iniciando tests de Protobuf")
    print("=" * 50)
    
    # Test 1: Importación directa
    test1_ok = test_protobuf_import()
    
    # Test 2: Event Collector
    test2_ok = test_event_collector_protobuf()
    
    print("\n" + "=" * 50)
    print("📋 Resumen de Tests:")
    print(f"  • Test Protobuf directo: {'✅ OK' if test1_ok else '❌ FAIL'}")
    print(f"  • Test Event Collector: {'✅ OK' if test2_ok else '❌ FAIL'}")
    
    if test1_ok and test2_ok:
        print("\n🎉 ¡Todos los tests pasaron! Protobuf está funcionando correctamente.")
        sys.exit(0)
    else:
        print("\n💥 Algunos tests fallaron.")
        sys.exit(1)
