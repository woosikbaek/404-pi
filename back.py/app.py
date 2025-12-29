import asyncio
import json
import signal
import sys
import paho.mqtt.client as mqtt
import bluetooth_manager as bt

# =====================
# MQTT 설정
# =====================
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

TOPIC_SENSOR_CONTROL = "sensor/control"
TOPIC_SENSOR_RESULT  = "sensor/result"

TOPIC_DRIVE_CONTROL  = "arm/complete"
TOPIC_DRIVE_STOP     = "drive/stop"  
TOPIC_DRIVE_RESULT   = "sensor/result"

# =====================
# 상태 플래그
# =====================
checking_in_progress = False
drive_requested = False
drive_running = False  

# =====================
# RESULT 파싱
# =====================
def parse_result(msg: str):
    """
    RESULT:
      LED / BUZ / ULT
      DRIVE
    """
    if not msg.startswith("RESULT:"):
        return None

    parts = msg.split(":")
    if len(parts) < 3:
        return None

    device = parts[1].strip()
    value  = parts[2].strip()
    
    # 주행 결과
    if device == "DRIVE":
        # SUCCESS만 OK로, 나머지는 모두 DEFECT로 처리
        if "SUCCESS" in value or "SUCC" in value:
            result_value = "OK"
        else:  # LINE_LOST, OBSTACLE 등 모든 실패 케이스
            result_value = "DEFECT"
        
        return {
            "topic": TOPIC_DRIVE_RESULT,
            "payload": {
                "device": "WHEEL",
                "result": result_value
            }
        }

    # 센서 결과
    # MakeCode 응답 형식을 백엔드 형식으로 변환
    device_map = {
        "BUZ": "BUZZER",
        "ULT": "ULTRASONIC"
    }
    backend_device = device_map.get(device, device)
    
    return {
        "topic": TOPIC_SENSOR_RESULT,
        "payload": {
            "device": backend_device,
            "result": value
        }
    }


# =====================
# Maqueen 명령 + 응답 대기
# =====================
async def send_and_wait(cmd, timeout=10.0):
    bt.clear_received_messages()
    await bt.send_command(cmd)

    limit = int(timeout / 0.1)
    for _ in range(limit):
        msgs = bt.get_received_messages()
        for msg in msgs:
            parsed = parse_result(msg)
            if parsed:
                return parsed
        await asyncio.sleep(0.1)

    return None


async def wait_for_result(device_filter=None, timeout=10.0):
    """
    명령 전송 없이 응답만 대기
    
    Args:
        device_filter (str): 특정 장치의 응답만 기다림 (예: "WHEEL", "LED")
        timeout (float): 타임아웃 시간 (초)
    
    Returns:
        dict: 파싱된 결과 또는 None
    """
    # 수신된 모든 메시지를 하나의 문자열로 모음
    all_messages = ""
    seen_messages = set()  # 이미 본 메시지 추적
    limit = int(timeout / 0.1)
    
    for i in range(limit):
        msgs = bt.get_received_messages()
        
        # 새로운 메시지만 추가
        for msg in msgs:
            if msg not in seen_messages:
                seen_messages.add(msg)
                # 디버그: 받은 메시지 출력 (한 번만)
                if msg.strip() and not msg.strip().startswith("HB"):
                    print(f" 수신 메시지: {msg.strip()}")
                all_messages += msg
        
        # 모든 메시지를 하나로 합쳐서 완전한 메시지 찾기
        combined = all_messages
        
        # 새줄 문자로 분리하여 각 메시지 처리
        for line in combined.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            # RESULT:로 시작하는 완전한 메시지만 파싱
            if line.startswith("RESULT:"):
                parsed = parse_result(line)
                if parsed:
                    # 필터가 지정된 경우 해당 장치의 응답만 반환
                    if device_filter is None or parsed["payload"]["device"] == device_filter:
                        # 응답 수신 후 버퍼 클리어하여 중복 방지
                        bt.clear_received_messages()
                        return parsed
        
        await asyncio.sleep(0.1)

    return None


# =====================
# 자동 점검
# =====================
async def auto_check():
    global checking_in_progress
    checking_in_progress = True

    for cmd in ["LED", "BUZ", "ULT"]:
        result = await send_and_wait(cmd, timeout=8)

        if result:
            mqtt_client.publish(
                result["topic"],
                json.dumps(result["payload"])
            )
        else:
            # timeout 시에도 백엔드 형식으로 변환
            device_map = {"BUZ": "BUZZER", "ULT": "ULTRASONIC"}
            backend_device = device_map.get(cmd, cmd)
            mqtt_client.publish(
                TOPIC_SENSOR_RESULT,
                json.dumps({
                    "device": backend_device,
                    "result": "timeout"
                })
            )

        await asyncio.sleep(0.3)

    checking_in_progress = False
    print("✅ 자동 점검 완료")


# =====================
# 주행 처리
# =====================
async def drive_sequence():
    global drive_running
    drive_running = True
    print("▶ 주행 시작")
    bt.clear_received_messages()
    
    # 명령 전송
    success = await bt.send_command("CMD:DRIVE_START")
    
    if not success:
        print("❌ 주행 명령 전송 실패 (블루투스 연결 확인 필요)")
        drive_running = False
        mqtt_client.publish(
            TOPIC_DRIVE_RESULT,
            json.dumps({
                "device": "WHEEL",
                "result": "DEFECT"
            })
        )
        return
    
    print(" 주행 응답 대기 중... (최대 20초)")
    await asyncio.sleep(0.5)  # 명령 처리 시작 대기
    
    # 주행 명령 전송 후 응답만 기다림 (명령어를 다시 보내지 않음)
    result = await wait_for_result(device_filter="WHEEL", timeout=20)

    if result:
        print(f"✅ 주행 응답 수신: {result['payload']}")
        mqtt_client.publish(
            result["topic"],
            json.dumps(result["payload"])
        )
    else:
        print("  주행 응답 없음 (timeout)")
        mqtt_client.publish(
            TOPIC_DRIVE_RESULT,
            json.dumps({
                "device": "WHEEL",
                "result": "timeout"
            })
        )
    
    drive_running = False

# =====================
# 주행 중단
# =====================
async def stop_drive():
    """마이크로비트로 주행 중단 명령 전송"""
    global drive_running
    print("🛑 주행 중단 명령 전송: CMD:STOP")
    success = await bt.send_command("CMD:STOP")
    
    if success:
        print("✅ 주행 중단 명령 전송 완료")
        drive_running = False
    else:
        print("❌ 주행 중단 명령 전송 실패")


# =====================
# MQTT 콜백
# =====================
def on_message(client, userdata, msg):
    global drive_requested

    payload = msg.payload.decode().strip()

    if msg.topic == TOPIC_SENSOR_CONTROL and payload.lower() == "true":
        if not checking_in_progress:
            asyncio.run_coroutine_threadsafe(auto_check(), loop)

    if msg.topic == TOPIC_DRIVE_CONTROL and payload.lower() == "true":
        drive_requested = True

    if msg.topic == TOPIC_DRIVE_STOP:
        if payload.lower() == "true" or payload.lower() == "stop":
            print("🛑 주행 중단 요청 수신")
            asyncio.run_coroutine_threadsafe(stop_drive(), loop)


# =====================
# 메인
# =====================
async def main():
    global mqtt_client, drive_requested

    if not await bt.connect():
        print("❌ BLE 연결 실패")
        return

    print("✅ BLE 연결 완료")

    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.subscribe([
        (TOPIC_SENSOR_CONTROL, 0),
        (TOPIC_DRIVE_CONTROL, 0),
        (TOPIC_DRIVE_STOP, 0)  # ✅ 추가: 주행 중단 토픽 구독
    ])
    mqtt_client.loop_start()

    print(" 시스템 대기 중...")
    print(f" 구독 토픽: {TOPIC_SENSOR_CONTROL}, {TOPIC_DRIVE_CONTROL}, {TOPIC_DRIVE_STOP}")
    print(f" 주행 시작 명령: mosquitto_pub -h localhost -t '{TOPIC_DRIVE_CONTROL}' -m 'true'")
    print(f" 주행 중단 명령: mosquitto_pub -h localhost -t '{TOPIC_DRIVE_STOP}' -m 'stop'")

    while True:
        if drive_requested:
            drive_requested = False
            await drive_sequence()

        await asyncio.sleep(0.1)


# =====================
# 실행
# =====================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message

try:
    loop.run_until_complete(main())
    loop.run_forever()
except KeyboardInterrupt:
    print("\n 종료")
finally:
    mqtt_client.loop_stop()
    loop.close()
