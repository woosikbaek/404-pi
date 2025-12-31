#!/usr/bin/env python3
"""
Maqueen RC카 Bluetooth 연결 관리자
micro:bit와의 블루투스 연결/해제/상태 관리를 담당
"""
import asyncio
import subprocess
from bleak import BleakClient, BleakScanner

# micro:bit 설정
MICROBIT_ADDRESS = "FD:38:D7:56:F0:07"
UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
# micro:bit MakeCode는 UUID를 반대로 구현함
UART_RX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # 라즈베리파이 → micro:bit (write)
UART_TX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # micro:bit → 라즈베리파이 (indicate)

# 전역 변수
_client = None
_received_messages = []
_notification_handler = None
_hb_task = None


def set_notification_handler(handler):
    """알림 핸들러 등록"""
    global _notification_handler
    _notification_handler = handler


def _internal_notification_handler(sender, data):
    """내부 알림 핸들러"""
    global _received_messages
    try:
        message = data.decode('utf-8').strip()
        _received_messages.append(message)
        
        # 외부 핸들러가 등록되어 있으면 호출
        if _notification_handler:
            _notification_handler(sender, data)
    except Exception as e:
        print(f"❌ 알림 처리 오류: {e}")


async def force_disconnect():
    """강제로 기존 연결 해제 (bluetoothctl 사용)"""
    try:
        subprocess.run(
            ['bluetoothctl', 'disconnect', MICROBIT_ADDRESS],
            capture_output=True,
            timeout=2
        )
        await asyncio.sleep(0.5)
    except:
        pass


# Heartbeat 송신 루프
async def _heartbeat_loop():
    """마이크로비트로 주기적으로 HB 신호 전송 (0.6초 주기)"""
    while _client and _client.is_connected:
        try:
            await _client.write_gatt_char(
                UART_RX_CHAR_UUID,
                b"HB\n"
            )
        except Exception as e:
            # 연결 오류 시 루프 종료
            break
        await asyncio.sleep(0.6)  # 600ms 주기 (0.3~0.8초 범위 내)

async def connect(max_retries=7):
    """
    micro:bit에 연결 (재시도 포함)
    
    Args:
        max_retries (int): 최대 재시도 횟수 (기본값: 7)
    
    Returns:
        bool: 연결 성공 여부
    """
    global _client, _received_messages, _hb_task
    
    # 시작 전 기존 연결 강제 해제
    await force_disconnect()
    await asyncio.sleep(1)
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f" 재시도 {attempt + 1}/{max_retries}...")
                await force_disconnect()
                await asyncio.sleep(4)
            
            # 1단계: 장치 스캔으로 먼저 찾기 (더 안정적)
            print(f" 장치 스캔 중... (10초)")
            device = await BleakScanner.find_device_by_address(MICROBIT_ADDRESS, timeout=10.0)
            
            if not device:
                print(f"❌ 장치를 찾을 수 없음 (시도 {attempt + 1}/{max_retries})")
                continue
            
            # 2단계: 발견된 장치 객체로 연결 (타임아웃 30초로 증가)
            _client = BleakClient(device, timeout=30.0)
            
            print(f" 연결 중... (최대 30초)")
            await _client.connect()
            
            if not _client.is_connected:
                print(f"❌ 연결 실패 (시도 {attempt + 1}/{max_retries})")
                continue
            
            print("✅ micro:bit 블루투스 연결 성공!")
            
            # 3단계: 서비스 확인 및 디버깅
            print(" 사용 가능한 서비스 확인 중...")
            services = _client.services  # get_services() 대신 services 속성 사용
            
            uart_service_found = False
            uart_tx_char = None
            
            for service in services:
                if UART_SERVICE_UUID.lower() in service.uuid.lower():
                    print(f"✅ UART 서비스 발견: {service.uuid}")
                    uart_service_found = True
                    
                    # 특성(Characteristics) 확인
                    for char in service.characteristics:
                        print(f"   특성: {char.uuid} (속성: {char.properties})")
                        if UART_TX_CHAR_UUID.lower() in char.uuid.lower():
                            uart_tx_char = char
                            print(f"   ✅ UART TX 특성 발견")
            
            if not uart_service_found:
                print("❌ UART 서비스를 찾을 수 없습니다!")
                print("   micro:bit 코드에 bluetooth.start_uart_service() 확인 필요")
                continue
            
            # 4단계: UART 알림 구독 시도 (notify 또는 indicate)
            if uart_tx_char and ("notify" in uart_tx_char.properties or "indicate" in uart_tx_char.properties):
                try:
                    print(" UART 알림 구독 시도...")
                    await _client.start_notify(UART_TX_CHAR_UUID, _internal_notification_handler)
                    print("✅ UART 알림 구독 완료")
                except Exception as e:
                    print(f" 알림 구독 실패: {e}")
                    print("   폴링 모드로 전환 (알림 없이 작동)")
            else:
                print("  UART TX 특성이 알림을 지원하지 않습니다")
            
            # 5단계: 연결 안정화 대기
            print("연결 안정화 중...")
            await asyncio.sleep(2)
            
            # 6단계: 수신 버퍼 초기화
            _received_messages.clear()
            
            # Heartbeat 송신 시작 (0.6초 주기로 HB 신호 전송)
            _hb_task = asyncio.create_task(_heartbeat_loop())
            print("✅ BLE 연결 성공 (Heartbeat 전송 시작: 0.6초 주기)")
            return True
        
        except asyncio.TimeoutError:
            print(f" 연결 시간 초과 (시도 {attempt + 1}/{max_retries})")
        except Exception as e:
            print(f"❌ BLE 오류 (시도 {attempt + 1}/{max_retries}): {e}")
            import traceback
            traceback.print_exc()
        
        # 연결 실패 시에만 정리 (성공하면 연결 유지)
        if _client:
            try:
                if _client.is_connected:
                    await _client.disconnect()
                    await asyncio.sleep(1)
            except:
                pass
            _client = None
    return False


async def disconnect():
    """micro:bit 연결 해제"""
    global _client, _hb_task
    
    if not _client:
        print(" 연결되지 않은 상태")
        return True
    
    if _hb_task:
        _hb_task.cancel()
        _hb_task = None

    if _client and _client.is_connected:
      await _client.disconnect()
      _client = None
    return True

def is_connected():
    """연결 상태 확인"""
    return _client is not None and _client.is_connected


async def send_command(command):
    """
    micro:bit로 명령 전송
    
    Args:
        command (str): 전송할 명령 (예: "check:LED")
    
    Returns:
        bool: 전송 성공 여부
    """
    global _client
    
    if not _client or not _client.is_connected:
        print("❌ 블루투스가 연결되지 않았습니다")
        return False
    
    try:
        message = f"{command}\n"
        print(f" BLE 명령 전송: {command.strip()}")
        await _client.write_gatt_char(UART_RX_CHAR_UUID, message.encode())
        print(f"✅ BLE 명령 전송 완료: {command.strip()}")
        return True
    except Exception as e:
        print(f"❌ 명령 전송 오류: {e}")
        return False


def get_received_messages():
    """수신된 메시지 목록 반환"""
    global _received_messages
    return _received_messages.copy()


def clear_received_messages():
    """수신된 메시지 버퍼 초기화"""
    global _received_messages
    _received_messages.clear()
