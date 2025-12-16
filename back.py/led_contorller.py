import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import json
import signal
import sys
# import serial
import time

RED = 17
GREEN = 27
BLUE = 22

MQTT_BROKER_CONTROL = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_CONTROL = "led/control"
MQTT_TOPIC_RESPONSE = "led/control/response"

# micro:bit 시리얼 포트 설정
MICROBIT_PORT = "/dev/ttyACM0"  # micro:bit이 연결된 포트 (환경에 따라 /dev/ttyUSB0 일 수도 있음)
MICROBIT_BAUDRATE = 115200

microbit_serial = None

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

# # micro:bit 시리얼 연결 초기화
# def setup_microbit():
#     global microbit_serial
#     try:
#         microbit_serial = serial.Serial(MICROBIT_PORT, MICROBIT_BAUDRATE, timeout=1)
#         time.sleep(2)  # micro:bit이 초기화될 시간을 줌
#         print(f"micro:bit 연결 완료: {MICROBIT_PORT}")
#         return True
#     except serial.SerialException as e:
#         print(f"micro:bit 연결 실패: {e}")
#         print("micro:bit이 연결되어 있는지 확인하세요.")
#         return False

# # micro:bit으로 LED 제어 명령 전송
# def send_to_microbit(led_state):
#     global microbit_serial
#     if microbit_serial and microbit_serial.is_open:
#         try:
#             command = f"{led_state}\n"  # ON 또는 OFF에 개행 추가
#             microbit_serial.write(command.encode())
#             print(f"micro:bit으로 전송: {led_state}")
#         except Exception as e:
#             print(f"micro:bit 전송 오류: {e}")
#     else:
#         print("micro:bit이 연결되어 있지 않습니다.")

# MQTT 메시지 수신 콜백 함수
def on_message(client, userdata, msg):
  try:
    message = json.loads(msg.payload.decode())
    print(f"수신된 메시지: {message}")
    if 'led' in message:
      led_state = message['led']  # 'ON' 또는 'OFF'
      current_state['state'] = led_state
      print(f"LED 상태 변경: {current_state['state']}")
      
      # micro:bit으로 LED 제어 명령 전송
      send_to_microbit(led_state)
      
    if 'buzzer' in message:
      current_state['buzzer'] = message['buzzer']
  except Exception as e:
    print(f"메시지 처리 중 오류 발생: {e}")

# MQTT 연결 해제 콜백 함수
def on_disconnect(client, userdata, rc):
    print("MQTT 연결이 해제되었습니다.")

# 프로그램 종료 시 리소스 정리 함수
def cleanup():
    global pwm_r, pwm_g, pwm_b, microbit_serial
    print("프로그램 종료 중...")
    pwm_r.stop()
    pwm_g.stop()
    pwm_b.stop()
    GPIO.cleanup()
    
    # micro:bit 시리얼 연결 종료
    if microbit_serial and microbit_serial.is_open:
        microbit_serial.close()
        print("micro:bit 연결 종료")
    
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
    
    # # micro:bit 연결
    # microbit_connected = setup_microbit()
    # if not microbit_connected:
    #     print("경고: micro:bit 없이 계속 진행합니다.")

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
