# 🚗 Maqueen RC카 자동 점검 시스템

라즈베리파이와 micro:bit를 활용한 Maqueen RC카의 센서 자동 점검 및 주행 제어 시스템입니다.

## 📋 프로젝트 개요

이 프로젝트는 라즈베리파이를 중앙 제어 장치로 사용하여 micro:bit 기반 Maqueen RC카의 센서를 자동으로 점검하고, MQTT를 통해 백엔드 서버와 통신하는 시스템입니다.

### 주요 기능

- ✅ **센서 자동 점검**: LED, 스피커, 초음파 센서 자동 점검
- ✅ **블루투스 통신**: micro:bit와 BLE(Bluetooth Low Energy) 통신
- ✅ **주행 제어**: 라인 트레이싱 주행 시작/중단 제어
- ✅ **카메라 제어**: USB 웹캠 2대를 활용한 동시 촬영
- ✅ **MQTT 통신**: 백엔드 서버와 실시간 데이터 교환

## 🏗️ 시스템 구조

```
┌─────────────┐      BLE       ┌──────────────┐
│  Raspberry  │ ◄──────────► │  micro:bit   │
│     Pi      │               │   (Maqueen)  │
└──────┬──────┘               └──────────────┘
       │
       │ MQTT
       │
┌──────▼──────┐
│   Backend   │
│   Server    │
└─────────────┘
```

## 📦 필수 요구사항

### 하드웨어
- Raspberry Pi (라즈베리파이)
- micro:bit V2
- DFRobot Maqueen Plus RC카
- USB 웹캠 2개
- 초음파 센서 (HC-SR04)

### 소프트웨어
- Python 3.13
- MQTT Broker (Mosquitto)
- OpenCV (cv2)
- Bluetooth 지원

## 🔧 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/your-username/404-pi.git
cd 404-pi
```

### 2. 가상 환경 설정

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

필수 패키지:
- `paho-mqtt`: MQTT 클라이언트
- `bleak`: BLE 통신 라이브러리
- `opencv-python`: 카메라 제어
- `asyncio`: 비동기 프로그래밍

### 4. MQTT Broker 설치 및 실행

```bash
# Ubuntu/Debian
sudo apt-get install mosquitto mosquitto-clients

# Broker 실행
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

## 🚀 사용 방법

### 1. micro:bit 설정

micro:bit에 MakeCode 프로그램을 업로드해야 합니다. 자세한 내용은 [README_MAKECODE.md](README_MAKECODE.md)를 참고하세요.

### 2. 블루투스 연결 설정

`bluetooth_manager.py`에서 micro:bit의 MAC 주소를 설정하세요:

```python
MICROBIT_ADDRESS = "FD:38:D7:56:F0:07"  # 본인의 micro:bit MAC 주소
```

### 3. 프로그램 실행

#### 센서 점검 및 주행 제어 (메인 애플리케이션)

```bash
cd back.py
python app.py
```

#### 카메라 제어

```bash
cd back.py
python camera.py
```

### 4. MQTT 명령 전송

#### 센서 점검 시작

```bash
mosquitto_pub -h localhost -t "ult01" -m "true"
```

#### 주행 시작

```bash
mosquitto_pub -h localhost -t "ult02" -m "true"
```

#### 주행 중단

```bash
mosquitto_pub -h localhost -t "drive/stop" -m "stop"
```

#### 결과 확인

```bash
mosquitto_sub -h localhost -t "sensor/result" -v
```

## 📁 프로젝트 구조

```
404-pi/
├── back.py/                 # 백엔드 Python 코드
│   ├── app.py              # 메인 애플리케이션 (센서 점검, 주행 제어)
│   ├── camera.py           # 카메라 제어 모듈
│   ├── bluetooth_manager.py # 블루투스 연결 관리
│   ├── drive.py            # 주행 제어 모듈
│   └── sensorCheck.py      # 센서 점검 모듈
├── README.md               # 프로젝트 메인 README
├── README_MAKECODE.md      # MakeCode 설정 가이드
├── README_MAQUEEN.md       # Maqueen 설정 가이드
├── PROBLEMS_AND_SOLUTIONS.md # 문제 해결 가이드
├── CAREER_EXPERIENCE.md    # 경력사항 항목
└── requirements.txt        # Python 패키지 목록
```

## 🔌 MQTT 토픽 구조

### 구독 토픽 (라즈베리파이 → 백엔드)

| 토픽 | 설명 | 메시지 형식 |
|------|------|------------|
| `ult01` | 센서 점검 시작 | `"true"` |
| `ult02` | 주행 시작 | `"true"` |
| `drive/stop` | 주행 중단 | `"stop"` 또는 `"true"` |
| `power/control` | 카메라 전원 제어 | `{"command": "POWER_ON"}` 또는 `{"command": "POWER_OFF"}` |

### 발행 토픽 (라즈베리파이 → 백엔드)

| 토픽 | 설명 | 메시지 형식 |
|------|------|------------|
| `sensor/result` | 센서 점검 결과 | `{"device": "LED", "result": "OK"}` |
| `camera01/control` | 카메라 이미지 전송 | `{"timestamp": 1234567890, "images": ["base64..."]}` |

## 🛠️ 주요 기능 설명

### 센서 점검

- **LED**: micro:bit 내장 LED를 켜고 조도 센서로 변화 감지
- **스피커**: 1000Hz 소리 재생 후 마이크로 소음 레벨 측정
- **초음파**: Maqueen Plus 초음파 센서로 거리 측정

### 블루투스 통신

- 자동 재연결 로직 (최대 7회 재시도)
- Heartbeat 메커니즘 (0.6초 주기)
- 메시지 중복 방지 및 필터링

### 카메라 제어

- USB 웹캠 2대 동시 제어
- 5초 간격 자동 촬영
- Base64 인코딩으로 MQTT 전송

## 🔧 문제 해결

주요 해결 사항:
- 블루투스 연결 안정성 개선 (성공률 30% → 95%)
- 메시지 중복 수신 문제 해결
- LED 센서 점검 정확도 향상 (성공률 60% → 90%)

## 📝 개발 환경

- **언어**: Python 3.7+
- **프레임워크**: asyncio (비동기 프로그래밍)
- **통신 프로토콜**: MQTT, BLE (Bluetooth Low Energy)
- **플랫폼**: Raspberry Pi OS (Linux)


---

⭐ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!

