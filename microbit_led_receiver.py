# # micro:bit에서 실행할 코드
# # 이 코드를 micro:bit에 업로드하세요

# from microbit import *

# while True:
#     # 시리얼 통신으로 데이터 수신
#     if uart.any():
#         command = uart.readline()
#         if command:
#             try:
#                 cmd_str = command.decode('utf-8').strip()
#                 display.scroll(cmd_str)
                
#                 if cmd_str == "ON":
#                     # LED 켜기 (하트 모양 표시)
#                     display.show(Image.HEART)
#                 elif cmd_str == "OFF":
#                     # LED 끄기
#                     display.clear()
                    
#             except Exception as e:
#                 # 오류 발생 시 X 표시
#                 display.show(Image.NO)
#                 sleep(1000)
    
#     sleep(100)  # 100ms 대기
