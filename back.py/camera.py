# 카메라 전원 on/off + 촬영 제어 모듈
import cv2
import paho.mqtt.client as mqtt
import json
import time
import base64
from datetime import datetime

# ======================
# MQTT 설정
# ======================
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

TOPIC_POWER = "power/control"
TOPIC_CAPTURE = "camera/capture"
TOPIC_CAMERA_SEND = "camera01/control"

# ======================
# 전역 상태 변수
# ======================
camera = None
camera_power = False

# ======================
# 로그 함수
# ======================
def log_message(message, level="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

# ======================
# 이미지 인코딩
# ======================
def encode_image_to_base64(image, max_width=320, quality=85):
    h, w = image.shape[:2]

    if w > max_width:
        scale = max_width / w
        image = cv2.resize(image, (max_width, int(h * scale)))

    _, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    return base64.b64encode(buffer).decode("utf-8")

# ======================
# 카메라 제어 함수
# ======================
def camera_power_on():
    global camera, camera_power
    if not camera_power:
        camera = cv2.VideoCapture(-1)  # -1로 자동 감지
        log_message("카메라 전원 ON 시도")
        time.sleep(1)  # 카메라 워밍업
        if not camera.isOpened():
            log_message("카메라 열기 실패", "ERROR")
            camera.release()
            camera = None
            return
        camera_power = True
        log_message("카메라 전원 ON 완료")

def camera_power_off():
    global camera, camera_power
    if camera_power:
        camera.release()
        camera = None
        camera_power = False

def capture_and_send_image():
    if not camera_power or camera is None:
        log_message("카메라가 꺼져 있어 촬영 불가", "WARNING")
        return

    ret, frame = camera.read()
    if not ret:
        log_message("사진 촬영 실패", "ERROR")
        return

    img_base64 = encode_image_to_base64(frame)

    message = {
        "camera_id": "camera01",
        "timestamp": time.time(),
        "image": img_base64
    }

    mqtt_client.publish(TOPIC_CAMERA_SEND, json.dumps(message))
    log_message("사진 촬영 후 AI 서버로 전송 완료")

# ======================
# MQTT 콜백
# ======================
def on_connect(client, userdata, flags, rc):
    log_message("MQTT 브로커 연결 완료")
    client.subscribe(TOPIC_POWER)
    client.subscribe(TOPIC_CAPTURE)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        log_message(f"수신 ({msg.topic}) : {payload}")

        command = payload.get("command")
        # 카메라 전원 제어
        if msg.topic == TOPIC_POWER:
            if command == "POWER_ON":
                camera_power_on()
                log_message("카메라 전원 ON 명령 처리 완료")
            elif command == "POWER_OFF":
                camera_power_off()
                log_message("카메라 전원 OFF 명령 처리 완료")

        # 촬영 명령
        if msg.topic == TOPIC_CAPTURE:
            if command == "CAMERA_CAPTURE":
              capture_and_send_image()

    except Exception as e:
        log_message(f"메시지 처리 오류: {e}", "ERROR")

# ======================
# 메인
# ======================
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def main():
    log_message("카메라 전원/촬영 제어 모듈 시작")
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()

if __name__ == "__main__":
    main()
