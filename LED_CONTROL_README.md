# LED 제어 시스템 - 백엔드 to micro:bit

## 구조
```
백엔드 (MQTT) → Raspberry Pi (led_controller.py) → micro:bit (시리얼 통신)
```

## 필요한 패키지 설치

```bash
pip install pyserial paho-mqtt
```

## 파일 설명

1. **led_controller.py** - 메인 프로그램
   - MQTT로 백엔드에서 메시지 수신
   - micro:bit으로 시리얼 통신으로 명령 전송

2. **microbit_led_receiver.py** - micro:bit용 코드
   - 시리얼 통신으로 명령 수신
   - LED 제어 (ON: 하트 표시, OFF: 화면 꺼짐)

3. **backend_simulator.py** - 백엔드 시뮬레이터
   - 테스트용 MQTT 메시지 전송 프로그램

## 사용 방법

### 1. micro:bit 설정

1. micro:bit을 USB로 Raspberry Pi에 연결
2. `microbit_led_receiver.py` 코드를 micro:bit에 업로드
   - Mu Editor 또는 온라인 Python Editor 사용
   - https://python.microbit.org/v/3 에서 업로드 가능

### 2. 시리얼 포트 확인

micro:bit이 연결된 포트를 확인:
```bash
ls /dev/tty*
# 보통 /dev/ttyACM0 또는 /dev/ttyUSB0
```

포트가 다르면 `led_controller.py`의 `MICROBIT_PORT` 수정:
```python
MICROBIT_PORT = "/dev/ttyACM0"  # 실제 포트로 변경
```

### 3. 실행

**터미널 1 - LED 컨트롤러 실행:**
```bash
python /home/kaghop/404-pi/back.py/led_controller.py
```

**터미널 2 - 백엔드 시뮬레이터 실행 (테스트용):**
```bash
python /home/kaghop/404-pi/backend_simulator.py
```

### 4. 메시지 형식

백엔드에서 보내는 MQTT 메시지:
```json
{"led": "ON"}   // LED 켜기
{"led": "OFF"}  // LED 끄기
```

토픽: `led/control`

## 문제 해결

### micro:bit 연결 실패
```bash
# 시리얼 포트 권한 부여
sudo chmod 666 /dev/ttyACM0
# 또는 사용자를 dialout 그룹에 추가
sudo usermod -a -G dialout $USER
```

### MQTT 브로커 확인
```bash
# mosquitto 실행 확인
sudo systemctl status mosquitto

# 없으면 설치
sudo apt-get install mosquitto mosquitto-clients
```

### 시리얼 통신 테스트
```bash
# screen으로 직접 테스트
screen /dev/ttyACM0 115200
# ON 또는 OFF 입력 후 Enter
```

## 실제 백엔드 연동

실제 백엔드가 있다면 `backend_simulator.py` 대신, 백엔드에서 다음과 같이 MQTT 메시지를 보내면 됩니다:

```python
import paho.mqtt.client as mqtt
import json

client = mqtt.Client()
client.connect("라즈베리파이IP", 1883, 60)
message = {'led': 'ON'}  # or {'led': 'OFF'}
client.publish("led/control", json.dumps(message))
client.disconnect()
```
