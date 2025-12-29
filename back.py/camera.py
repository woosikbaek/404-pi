import cv2
import paho.mqtt.client as mqtt
import json
import time
import base64
import threading
from datetime import datetime

# ======================
# MQTT 설정
# ======================
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

TOPIC_POWER = "power/control"
TOPIC_CAMERA_SEND = "camera01/control"

# ======================
# 카메라 디바이스 고정 (USB 웹캠 2개)
# ======================
CAMERA_DEVICES = {
    1: 0,
    2: 2
}

# ======================
# 전역 상태
# ======================
cams = {1: None, 2: None}
camera_power = False

auto_capture_thread = None
auto_capture_running = False
CAPTURE_INTERVAL = 5  # 초

# ======================
# 로그
# ======================
def log(msg, level="INFO"):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {msg}")

# ======================
# 이미지 인코딩 (PNG 유지)
# ======================
def encode_png(image, max_width=320):
    h, w = image.shape[:2]
    if w > max_width:
        scale = max_width / w
        image = cv2.resize(image, (max_width, int(h * scale)))

    _, buffer = cv2.imencode(".png", image)
    return base64.b64encode(buffer).decode()

# ======================
# 카메라 전원 ON
# ======================
def camera_power_on():
    global camera_power, cams

    if camera_power:
        log("카메라 이미 ON 상태")
        return

    log("카메라 전원 ON 시작")

    for num in [1, 2]:
        index = CAMERA_DEVICES[num]
        cam = cv2.VideoCapture(index, cv2.CAP_V4L2)
        cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cam.set(cv2.CAP_PROP_FPS, 15)
        cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        time.sleep(2.0)  # 워밍업

        ret, _ = cam.read()
        if not ret:
            log(f"카메라 {num} 열기 실패 (index: {index})", "ERROR")
            cam.release()
            camera_power_off()
            return

        cams[num] = cam
        log(f"카메라 {num} ON 완료")

    camera_power = True
    start_auto_capture()

# ======================
# 카메라 전원 OFF
# ======================
def camera_power_off():
    global camera_power, cams

    stop_auto_capture()

    for num in [1, 2]:
        if cams[num]:
            cams[num].release()
            cams[num] = None
            log(f"카메라 {num} OFF")

    camera_power = False

# ======================
# 자동 촬영 루프
# ======================
def auto_capture_loop():
    global auto_capture_running

    log("자동 촬영 시작")

    while auto_capture_running:
        try:
            ret1, frame1 = cams[1].read()
            ret2, frame2 = cams[2].read()

            if ret1 and ret2:
                send_image(frame1, "camera01")
                send_image(frame2, "camera02")
            else:
                log("프레임 수신 실패", "WARNING")

            for _ in range(CAPTURE_INTERVAL):
                if not auto_capture_running:
                    break
                time.sleep(1)

        except Exception as e:
            log(f"자동 촬영 오류: {e}", "ERROR")
            time.sleep(1)

    log("자동 촬영 종료")

def start_auto_capture():
    global auto_capture_running, auto_capture_thread

    if not auto_capture_running:
        auto_capture_running = True
        auto_capture_thread = threading.Thread(
            target=auto_capture_loop, daemon=True
        )
        auto_capture_thread.start()

def stop_auto_capture():
    global auto_capture_running, auto_capture_thread

    if auto_capture_running:
        auto_capture_running = False
        if auto_capture_thread:
            auto_capture_thread.join(timeout=2)

# ======================
# 이미지 전송
# ======================
def send_image(frame, camera_id):
    payload = {
        "timestamp": time.time(),
        "image": encode_png(frame)
    }
    mqtt_client.publish(TOPIC_CAMERA_SEND, json.dumps(payload))
    log(f"{camera_id} 이미지 전송 완료")

# ======================
# MQTT 콜백
# ======================
def on_connect(client, userdata, flags, rc):
    log("MQTT 연결 완료")
    client.subscribe(TOPIC_POWER)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        command = payload.get("command")

        if msg.topic == TOPIC_POWER:
            if command == "POWER_ON":
                camera_power_on()
            elif command == "POWER_OFF":
                camera_power_off()

    except Exception as e:
        log(f"MQTT 처리 오류: {e}", "ERROR")

# ======================
# 메인
# ======================
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def main():
    log("카메라 제어 모듈 시작")
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()

if __name__ == "__main__":
    main()
