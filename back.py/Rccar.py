bluetooth.start_uart_service()
basic.show_icon(IconNames.HEART)
import maqueen

last_hb_time = control.millis()
HB_TIMEOUT = 1500  # ms (1.5초)
hb_initialized = False
sensor_checking = False  #  센서 점검 중 플래그

# =====================
# 상태 정의
# =====================
MODE_IDLE = 0
MODE_DRIVE = 2
MODE_ERROR = 3

mode = MODE_IDLE

# =====================
# Maqueen 핀 정의
# =====================

TRIG = DigitalPin.P1
ECHO = DigitalPin.P2

# =====================
# BLE 수신
# =====================
def on_uart_data():
    global mode, drive_start_time, line_lost_count, searching_for_line
    global last_hb_time, hb_initialized, drive_success

    cmd = bluetooth.uart_read_until(
        serial.delimiters(Delimiters.NEW_LINE)
    ).strip()

    if cmd == "HB":
        last_hb_time = control.millis()
        hb_initialized = True
        #  HB 신호 받으면 LED 끄기 (정상 상태)
        if mode == MODE_IDLE:
            basic.clear_screen()
        return
    elif cmd == "LED":
        check_led()
    elif cmd == "BUZ":
        check_buzzer()
    elif cmd == "ULT":
        check_ultrasonic()
    elif cmd == "CMD:DRIVE_START":
        if sensor_checking:
            return
        drive_start_time = control.millis()
        line_lost_count = 0
        searching_for_line = False
        drive_success = False
        last_motor_time = 0
        mode = MODE_DRIVE
        # 주행 시작 전 라인 확인
        basic.pause(100)
        line_left = maqueen.read_patrol(maqueen.Patrol.PATROL_LEFT)
        line_right = maqueen.read_patrol(maqueen.Patrol.PATROL_RIGHT)

        if line_left == 0 or line_right == 0:
            # 라인이 있으면 바로 시작 가능
            motor_forward(35, 35)
            last_motor_time = control.millis()
        else:
            # 라인이 없으면 찾기 시작
            searching_for_line = True
            line_lost_count = 0
            motor_turn_left(15)
            last_motor_time = control.millis()
    elif cmd == "CMD:STOP":
        motor_stop()
        mode = MODE_IDLE
        basic.clear_screen()  #  정지 시 LED 끄기


bluetooth.on_uart_data_received(
    serial.delimiters(Delimiters.NEW_LINE),
    on_uart_data
)

# =====================
# 유틸
# =====================
def send(msg: str):
    bluetooth.uart_write_string(msg + "\n")

def motor_stop():
    maqueen.motor_stop(maqueen.Motors.ALL)

def motor_forward(l, r):
    maqueen.motor_run(maqueen.Motors.M1, maqueen.Dir.CW, l)
    maqueen.motor_run(maqueen.Motors.M2, maqueen.Dir.CW, r)

def motor_turn_left(speed):
    maqueen.motor_run(maqueen.Motors.M1, maqueen.Dir.CW, 0)
    maqueen.motor_run(maqueen.Motors.M2, maqueen.Dir.CW, speed)

def motor_turn_right(speed):
    maqueen.motor_run(maqueen.Motors.M1, maqueen.Dir.CW, speed)
    maqueen.motor_run(maqueen.Motors.M2, maqueen.Dir.CW, 0)


# =====================
# 센서 점검
# =====================
def check_led():
    global sensor_checking
    sensor_checking = True

    success_count = 0

    for attempt in range(2):
        basic.clear_screen()
        basic.pause(600)
        off_light = input.light_level()

        basic.show_leds("""
            . . . . .
            . # # # .
            . # # # .
            . # # # .
            . . . . .
        """)
        basic.pause(800)
        on_light = input.light_level()

        if on_light >= off_light:
            success_count += 1

        basic.pause(400)

    basic.clear_screen()
    sensor_checking = False

    if success_count >= 1:
        send("RESULT:LED:OK")
    else:
        send("RESULT:LED:DEFECT")



def check_buzzer():
    global sensor_checking
    sensor_checking = True  #  센서 점검 시작
    detected = False

    for _ in range(3):
        pins.analog_set_pitch_pin(AnalogPin.P0)
        pins.analog_pitch(1000, 1000)

        basic.pause(200)
        s1 = input.sound_level()
        basic.pause(200)
        s2 = input.sound_level()
        basic.pause(200)
        s3 = input.sound_level()

        pins.analog_pitch(0, 0)
        pins.digital_write_pin(DigitalPin.P0, 0)

        mx = s1
        if s2 > mx:
            mx = s2
        if s3 > mx:
            mx = s3

        if mx >= 15:
            detected = True
            break

        basic.pause(500)

    sensor_checking = False  # 센서 점검 완료
    
    if detected:
        send("RESULT:BUZ:OK")
    else:
        send("RESULT:BUZ:DEFECT")

def check_ultrasonic():
    global sensor_checking
    sensor_checking = True  #  센서 점검 시작
    valid = 0

    for _ in range(3):
        pins.digital_write_pin(TRIG, 0)
        control.wait_micros(2)
        pins.digital_write_pin(TRIG, 1)
        control.wait_micros(10)
        pins.digital_write_pin(TRIG, 0)

        dur = pins.pulse_in(ECHO, PulseValue.HIGH, 25000)
        if dur > 0:
            dist = dur / 59
            if 2 <= dist <= 400:
                valid += 1

        basic.pause(600)

    sensor_checking = False  #  센서 점검 완료
    
    if valid >= 2:
        send("RESULT:ULT:OK")
    else:
        send("RESULT:ULT:DEFECT")

# =====================
# 주행 로직
# =====================
drive_start_time = 0
line_lost_count = 0
drive_success = False
searching_for_line = False  # 라인 찾기 모드 플래그
last_motor_time = 0

def line_trace_step():
    global line_lost_count, searching_for_line, last_motor_time, drive_success

    line_left = maqueen.read_patrol(maqueen.Patrol.PATROL_LEFT)
    line_right= maqueen.read_patrol(maqueen.Patrol.PATROL_RIGHT)

    if line_right == 0 and line_left == 0:
        motor_forward(35, 35)
        line_lost_count = 0
        searching_for_line = False
        last_motor_time = control.millis()
        drive_success = True
        return
    elif line_right == 0:
        motor_turn_right(25)
        line_lost_count = 0
        searching_for_line = False
        last_motor_time = control.millis()
        return
    elif line_left == 0:
        motor_turn_left(25)
        line_lost_count = 0
        searching_for_line = False
        last_motor_time = control.millis()
        return
    else:
        # 라인을 잃었을 때
        if not searching_for_line:
            searching_for_line = True
            line_lost_count = 0
        
        line_lost_count += 1
        
        # 라인 찾기: 좌우로 회전하며 탐색
        if line_lost_count <= 30:  # 약 1초 동안 탐색 (30 * 30ms)
            # 좌우 번갈아 회전
            if line_lost_count % 4 < 2:
                motor_turn_left(25)
            else:
                motor_turn_right(25)
            last_motor_time = control.millis()
        elif line_lost_count <= 60:  # 더 넓게 탐색
            # 더 큰 각도로 회전
            if line_lost_count % 6 < 3:
                motor_turn_left(25)
            else:
                motor_turn_right(25)
            last_motor_time = control.millis()
        else:
            # 라인을 찾지 못함
            motor_stop()
            return
        basic.pause(30)  # 회전 후 잠시 대기
        line_left = maqueen.read_patrol(maqueen.Patrol.PATROL_LEFT)
        line_right = maqueen.read_patrol(maqueen.Patrol.PATROL_RIGHT)

        
        # 라인을 찾았으면 즉시 복귀
        if line_right == 0 or line_left == 0:
            line_lost_count = 0
            searching_for_line = False
            # 라인 방향으로 바로 조정
            if line_right == 0:
                motor_turn_right(25)
            elif line_left == 0:
                motor_turn_left(25)
            last_motor_time = control.millis()
            return

# =====================
# 메인 루프
# =====================
while True:
    if mode != MODE_DRIVE:
        #  센서 점검 중이면 LED 제어 안 함 (점검 중단 방지)
        if not sensor_checking:
            #  HB 타임아웃 체크: 끊겼을 때만 NO 아이콘 표시
            if control.millis() - last_hb_time > HB_TIMEOUT:
                motor_stop()
                mode = MODE_IDLE
                basic.show_icon(IconNames.NO)  #  HB 끊겼을 때만 NO 아이콘 표시
                basic.pause(100)
                continue
            else:
                #  HB 정상이면 LED 끄기 (IDLE 모드일 때만, 센서 점검 중이 아닐 때만)
                if hb_initialized:
                    basic.clear_screen()
                
    if mode == MODE_DRIVE:
        line_trace_step()
        if hb_initialized and control.millis() - last_hb_time > 5000:
            # 5초 이상 HB가 없으면 주행 종료
            motor_stop()
            mode = MODE_IDLE
            basic.clear_screen()  #  주행 종료 시 LED 끄기
            continue

        if control.millis() - drive_start_time > 10000:
                motor_stop()
                line_left = maqueen.read_patrol(maqueen.Patrol.PATROL_LEFT)
                line_right = maqueen.read_patrol(maqueen.Patrol.PATROL_RIGHT)

                if drive_success:
                    motor_stop()
                    send("RESULT:DRIVE:SUCCESS")
                else:
                    motor_stop()
                    send("RESULT:DRIVE:FAIL")
                mode = MODE_IDLE
                basic.clear_screen()  #  주행 완료 시 LED 끄기
                

    basic.pause(30)

