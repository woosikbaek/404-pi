# #!/usr/bin/env python3
# """
# 백엔드 시뮬레이터 - MQTT로 LED 제어 메시지 전송
# """
# import paho.mqtt.client as mqtt
# import json
# import time

# MQTT_BROKER = "localhost"
# MQTT_PORT = 1883
# MQTT_TOPIC = "led/control"

# def send_led_command(command):
#     """LED ON/OFF 명령 전송"""
#     client = mqtt.Client()
    
#     try:
#         client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
#         # JSON 메시지 생성
#         message = {'led': command}
#         payload = json.dumps(message)
        
#         # 메시지 전송
#         client.publish(MQTT_TOPIC, payload)
#         print(f"메시지 전송: {message}")
        
#         client.disconnect()
        
#     except Exception as e:
#         print(f"오류 발생: {e}")

# if __name__ == "__main__":
#     print("백엔드 시뮬레이터 시작")
#     print("LED 제어 명령을 전송합니다...")
    
#     while True:
#         print("\n1. LED ON")
#         print("2. LED OFF")
#         print("3. 종료")
#         choice = input("선택: ")
        
#         if choice == "1":
#             send_led_command("ON")
#         elif choice == "2":
#             send_led_command("OFF")
#         elif choice == "3":
#             print("종료합니다.")
#             break
#         else:
#             print("잘못된 입력입니다.")
