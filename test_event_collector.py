#!/usr/bin/env python3
"""
Script de prueba para el Event Collector
"""
import asyncio
import aiohttp
import json
import time
import uuid
from typing import Dict, Any


async def test_event_collector():
    """Probar el Event Collector"""
    base_url = "http://localhost:8000"
    
    print("🧪 Iniciando pruebas del Event Collector...")
    
    async with aiohttp.ClientSession() as session:
        
        # 1. Test Health Check
        print("\n1️⃣ Testing Health Check...")
        try:
            async with session.get(f"{base_url}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ Health Status: {data['status']}")
                    print(f"   📊 Service: {data['service_name']} v{data['version']}")
                else:
                    print(f"   ❌ Health check failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 2. Test Root Endpoint
        print("\n2️⃣ Testing Root Endpoint...")
        try:
            async with session.get(f"{base_url}/") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ Service: {data.get('service', 'Unknown')}")
                    print(f"   📋 Available endpoints: {len(data.get('endpoints', {}))}")
                else:
                    print(f"   ❌ Root endpoint failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 3. Test Click Collection
        print("\n3️⃣ Testing Click Collection...")
        click_data = {
            "campaign_id": "camp-test-001",
            "partner_id": "partner-test-123",
            "session_id": f"session-{uuid.uuid4()}",
            "utm_params": {
                "utm_source": "test",
                "utm_medium": "api",
                "utm_campaign": "load_test"
            },
            "custom_params": {
                "test_type": "automated",
                "timestamp": str(int(time.time()))
            }
        }
        
        try:
            start_time = time.time()
            async with session.post(
                f"{base_url}/collect/click",
                json=click_data,
                headers={"Content-Type": "application/json"}
            ) as resp:
                end_time = time.time()
                
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ Click registered: {data['click_id']}")
                    print(f"   ⚡ Response time: {(end_time - start_time) * 1000:.2f}ms")
                    print(f"   📝 Status: {data['status']}")
                else:
                    error_data = await resp.text()
                    print(f"   ❌ Click collection failed: {resp.status}")
                    print(f"   📄 Error: {error_data}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 4. Test Impression Collection
        print("\n4️⃣ Testing Impression Collection...")
        impression_data = {
            "campaign_id": "camp-test-001",
            "partner_id": "partner-test-123",
            "ad_creative_id": "creative-banner-001",
            "placement_id": "placement-sidebar",
            "view_duration_ms": 5000
        }
        
        try:
            async with session.post(
                f"{base_url}/collect/impression",
                json=impression_data,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ Impression registered: {data['impression_id']}")
                else:
                    print(f"   ❌ Impression collection failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 5. Test Conversion Collection
        print("\n5️⃣ Testing Conversion Collection...")
        conversion_data = {
            "campaign_id": "camp-test-001",
            "partner_id": "partner-test-123",
            "conversion_type": "PURCHASE",
            "value_amount": 99.99,
            "value_currency": "USD",
            "order_id": f"order-{uuid.uuid4()}",
            "conversion_data": {
                "product_id": "prod-123",
                "category": "electronics"
            }
        }
        
        try:
            async with session.post(
                f"{base_url}/collect/conversion",
                json=conversion_data,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ Conversion registered: {data['conversion_id']}")
                    if data.get('attributed_click_id'):
                        print(f"   🔗 Attributed to click: {data['attributed_click_id']}")
                else:
                    print(f"   ❌ Conversion collection failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 6. Test Load (múltiples clicks)
        print("\n6️⃣ Testing Load (10 clicks)...")
        start_time = time.time()
        success_count = 0
        
        tasks = []
        for i in range(10):
            click_data_load = {
                "campaign_id": f"camp-load-{i % 3}",  # 3 campañas diferentes
                "partner_id": f"partner-{i % 5}",     # 5 partners diferentes
                "utm_params": {"utm_source": "load_test", "batch": str(i)}
            }
            
            task = session.post(
                f"{base_url}/collect/click",
                json=click_data_load,
                headers={"Content-Type": "application/json"}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                print(f"   ❌ Click {i+1} failed: {response}")
            else:
                if response.status == 200:
                    success_count += 1
                response.close()
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        print(f"   📊 Load test results:")
        print(f"     - Total requests: 10")
        print(f"     - Successful: {success_count}")
        print(f"     - Failed: {10 - success_count}")
        print(f"     - Total time: {total_time:.2f}ms")
        print(f"     - Average time per request: {total_time / 10:.2f}ms")
        
        if success_count >= 8:  # Al menos 80% de éxito
            print(f"   ✅ Load test passed!")
        else:
            print(f"   ⚠️ Load test degraded (success rate: {success_count/10*100:.1f}%)")


async def test_original_pagos():
    """Probar el módulo de pagos original"""
    base_url = "http://localhost:8000"
    
    print("\n\n💳 Testing Original Pagos Module...")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test crear pago
            pago_data = {
                "monto": 100.50,
                "moneda": "USD",
                "destinatario": "partner-test-123"
            }
            
            async with session.post(
                f"{base_url}/api/pagos/",
                json=pago_data,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    print(f"   ✅ Pago creado: {data.get('id_pago')}")
                    print(f"   💰 Monto: {data.get('monto')} {data.get('moneda')}")
                    return data.get('id_pago')
                else:
                    error_data = await resp.text()
                    print(f"   ❌ Error creando pago: {resp.status}")
                    print(f"   📄 Error: {error_data}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return None


if __name__ == "__main__":
    print("🚀 ALPES Partners - Event Collector Test Suite")
    print("=" * 50)
    
    try:
        # Test Event Collector
        asyncio.run(test_event_collector())
        
        # Test Pagos module
        asyncio.run(test_original_pagos())
        
        print("\n" + "=" * 50)
        print("✅ Test suite completed!")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
