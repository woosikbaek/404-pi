import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import json
import signal
import sys

RED = 17
GREEN = 27
BLUE = 22

MQTT_BROKER_CONTROL = "localhost"
MQTT_BROKER_RESPONSE = "yeonjae"
MQTT_PORT = 1883
MQTT_TOPIC_CONTROL = "led/control"
MQTT_TOPIC_RESPONSE = "led/control/response"

pwm_r = None
pwm_g = None
pwm_b = None

current_state = {
  'state' : 'OFF',
  'buzzer' : 'OFF',
}

# GPIO 초기화 함수
def setup_gpio():
    global pwm_r, pwm_g, pwm_b
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(RED, GPIO.OUT)
    GPIO.setup(GREEN, GPIO.OUT)
    GPIO.setup(BLUE, GPIO.OUT)

    # pwm 객체 생성 1000은 주파수 값
    # 값이 낮을 수록 깜빡깜빡 하는 것이 눈에 보임
    pwm_r = GPIO.PWM(RED, 1000)
    pwm_g = GPIO.PWM(GREEN, 1000)
    pwm_b = GPIO.PWM(BLUE, 1000)

    # 초기 밝기 값을 0으로 즉, 꺼진 상태
    pwm_r.start(0)
    pwm_g.start(0)
    pwm_b.start(0)

    print("GPIO 초기화 완료")

# MQTT 메시지 수신 콜백 함수
def on_message(client, userdata, msg):
  try:
    message = json.loads(msg.payload.decode())
    print(f"수신된 메시지: {message}")
    if 'led' in message:
      current_state['state'] = message['led']
    if 'buzzer' in message:
      current_state['buzzer'] = message['buzzer']
  except Exception as e:
    print(f"메시지 처리 중 오류 발생: {e}")

# MQTT 연결 해제 콜백 함수
def on_disconnect(client, userdata, rc):
    print("MQTT 연결이 해제되었습니다.")

# 프로그램 종료 시 리소스 정리 함수
def cleanup():
    global pwm_r, pwm_g, pwm_b
    print("프로그램 종료 중...")
    pwm_r.stop()
    pwm_g.stop()
    pwm_b.stop()
    GPIO.cleanup()
    mqtt_client.disconnect() # mqtt 연결 해제
    print("정리 완료. 종료합니다.")
    sys.exit(0)

# 시그널 핸들러 등록
def signal_handler(sig, frame):
    cleanup()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT 브로커에 성공적으로 연결되었습니다.")
        client.subscribe(MQTT_TOPIC_CONTROL)
        print('토픽 구독 완료')
    else:
        print("MQTT 브로커 연결 실패")

# 실제로 실행할 메인 함수
def main():
    global mqtt_client
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler) # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler) # 프로세스 직접 종료
    
    # GPIO 세팅
    setup_gpio()

    # MQTT 클라이언트 설정
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect

    try:
      mqtt_client.connect(MQTT_BROKER_CONTROL, MQTT_PORT, 60)
      mqtt_client.loop_forever()
    except Exception as e:
      print(f"MQTT 브로커 연결 중 오류 발생: {e}")
      cleanup()
if __name__ == "__main__":
    main()
