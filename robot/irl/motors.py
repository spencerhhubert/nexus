from pyfirmata import util
import time
import threading
import math
from typing import Dict, Any, List, Optional, cast
from robot.global_config import GlobalConfig
from robot.irl.our_arduino import OurArduinoMega


class PCA9685:
    def __init__(self, gc: GlobalConfig, dev: OurArduinoMega, addr: int):
        self.gc = gc
        self.dev = dev
        self.addr = addr
        dev.sysex(0x01, [0x07, self.addr])


class Servo:
    def __init__(self, gc: GlobalConfig, channel: int, dev: PCA9685):
        self.gc = gc
        self.channel = channel
        self.dev = dev
        self._current_angle = 0

    def setAngle(self, angle: int, duration: Optional[int] = None) -> None:
        if duration is None:
            self.gc["logger"].info(
                f"Setting servo on channel {self.channel} and board {self.dev.addr} to {angle} degrees"
            )
            data = [
                0x08,
                self.dev.addr,
                self.channel,
                util.to_two_bytes(angle)[0],
                util.to_two_bytes(angle)[1],
            ]
            self.dev.dev.sysex(0x01, data)
            self._current_angle = angle
        else:
            self._setAngleGradually(angle, duration)

    def _setAngleGradually(
        self, target_angle: int, duration_ms: int, step_delay_ms: int = 50
    ) -> None:
        current_angle = self._current_angle

        total_steps = max(1, duration_ms // step_delay_ms)
        angle_step = (target_angle - current_angle) / total_steps

        self.gc["logger"].info(
            f"Moving servo on channel {self.channel} from {current_angle} to {target_angle} degrees over {duration_ms}ms"
        )

        for step in range(total_steps):
            intermediate_angle = int(current_angle + (angle_step * step))
            data = [
                0x08,
                self.dev.addr,
                self.channel,
                util.to_two_bytes(intermediate_angle)[0],
                util.to_two_bytes(intermediate_angle)[1],
            ]
            self.dev.dev.sysex(0x01, data)
            time.sleep(step_delay_ms / 1000.0)

        # Ensure we end at the exact target angle
        data = [
            0x08,
            self.dev.addr,
            self.channel,
            util.to_two_bytes(target_angle)[0],
            util.to_two_bytes(target_angle)[1],
        ]
        self.dev.dev.sysex(0x01, data)
        self._current_angle = target_angle

    def turnOff(self) -> None:
        self.gc["logger"].info(
            f"Turning off servo on channel {self.channel} and board {self.dev.addr}"
        )
        data = [
            0x09,
            self.dev.addr,
            self.channel,
        ]
        self.dev.dev.sysex(0x01, data)

    def setAngleAndTurnOff(self, angle: int, turn_off_delay_ms: int) -> None:
        self.setAngle(angle)

        def turnOffAfterDelay():
            time.sleep(turn_off_delay_ms / 1000.0)
            self.turnOff()

        thread = threading.Thread(target=turnOffAfterDelay, daemon=True)
        thread.start()


class DCMotor:
    def __init__(
        self,
        gc: GlobalConfig,
        dev: OurArduinoMega,
        enable_pin: int,
        input_1_pin: int,
        input_2_pin: int,
    ):
        self.gc = gc
        self.dev = dev
        self.enable_pin = enable_pin
        self.input_1_pin = input_1_pin
        self.input_2_pin = input_2_pin

        logger = gc["logger"]
        logger.info(f"Setting pin {self.input_1_pin} to OUTPUT")
        self.dev.sysex(0x03, [0x01, self.input_1_pin, 1])
        logger.info(f"Setting pin {self.input_2_pin} to OUTPUT")
        self.dev.sysex(0x03, [0x01, self.input_2_pin, 1])
        logger.info(f"Setting pin {self.enable_pin} to OUTPUT")
        self.dev.sysex(0x03, [0x01, self.enable_pin, 1])

    def setSpeed(self, speed: int) -> None:
        original_speed = speed
        speed = max(-255, min(255, speed))

        logger = self.gc["logger"]
        logger.info(f"DCMotor setSpeed: requested={original_speed}, clamped={speed}")
        logger.info(
            f"Using pins: enable={self.enable_pin}, input1={self.input_1_pin}, input2={self.input_2_pin}"
        )

        if speed > 0:
            logger.info("Setting FORWARD: IN1=HIGH, IN2=LOW")
            self.dev.sysex(0x03, [0x02, self.input_1_pin, 1])
            self.dev.sysex(0x03, [0x02, self.input_2_pin, 0])
        elif speed < 0:
            logger.info("Setting REVERSE: IN1=LOW, IN2=HIGH")
            self.dev.sysex(0x03, [0x02, self.input_1_pin, 0])
            self.dev.sysex(0x03, [0x02, self.input_2_pin, 1])
        else:
            logger.info("Setting STOP: IN1=LOW, IN2=LOW")
            self.dev.sysex(0x03, [0x02, self.input_1_pin, 0])
            self.dev.sysex(0x03, [0x02, self.input_2_pin, 0])

        pwm_value = int(abs(speed))
        logger.info(f"Setting enable pin {self.enable_pin} to PWM value: {pwm_value}")
        self.dev.sysex(0x03, [0x03, self.enable_pin, pwm_value])


class BreakBeamSensor:
    def __init__(self, gc: GlobalConfig, dev: OurArduinoMega, sensor_pin: int):
        self.gc = gc
        self.dev = dev
        self.sensor_pin = sensor_pin
        self.last_query_timestamp = 0

        logger = gc["logger"]
        logger.info(f"Setting up break beam sensor on pin {sensor_pin}")

        self.dev.add_cmd_handler(0x60, self._onBreakBeamResponse)
        self.dev.sysex(0x60, [0x01, sensor_pin])

        time.sleep(0.1)
        logger.info(f"Break beam sensor initialized on pin {sensor_pin}")

    def queryBreakings(self, since_timestamp: int) -> tuple[int, int]:
        timestamp_bytes = [
            (since_timestamp >> 0) & 0x7F,
            (since_timestamp >> 7) & 0x7F, 
            (since_timestamp >> 14) & 0x7F,
            (since_timestamp >> 21) & 0x7F,
            (since_timestamp >> 28) & 0x7F
        ]
        
        self.dev.sysex(0x60, [0x02] + timestamp_bytes)
        time.sleep(0.01)
        
        if hasattr(self, 'last_break_timestamp') and hasattr(self, 'last_query_timestamp'):
            return (self.last_break_timestamp, self.last_query_timestamp)
        else:
            return (-1, int(time.time() * 1000))

    def _onBreakBeamResponse(self, *args):
        if len(args) >= 10:
            break_timestamp = (args[0] | (args[1] << 7) | (args[2] << 14) | 
                             (args[3] << 21) | (args[4] << 28))
            latest_timestamp = (args[5] | (args[6] << 7) | (args[7] << 14) | 
                              (args[8] << 21) | (args[9] << 28))
            
            if break_timestamp == 0xFFFFFFFF:
                break_timestamp = -1
                
            self.last_break_timestamp = break_timestamp
            self.last_query_timestamp = latest_timestamp


class Encoder:
    def __init__(
        self,
        gc: GlobalConfig,
        dev: OurArduinoMega,
        clk_pin: int,
        dt_pin: int,
        pulses_per_revolution: int,
        wheel_diameter_mm: float,
    ):
        self.gc = gc
        self.dev = dev
        self.clk_pin = clk_pin
        self.dt_pin = dt_pin
        self.pulses_per_revolution = pulses_per_revolution
        self.wheel_diameter_cm = wheel_diameter_mm / 10  # Convert mm to cm
        self.wheel_circumference_cm = math.pi * self.wheel_diameter_cm

        self.pulse_count = 0
        self.last_update_time = time.time()
        self.lock = threading.Lock()

        self.last_encoder_position = 0

        logger = gc["logger"]
        logger.info(f"Setting up encoder with CLK={self.clk_pin}, DT={self.dt_pin}")

        self.dev.add_cmd_handler(
            0x50, self._onEncoderResponse
        )  # Register sysex handler for encoder responses
        self.dev.sysex(0x50, [0x01, self.clk_pin, self.dt_pin])  # ENCODER_SETUP command

        time.sleep(0.1)

        self.polling_thread = threading.Thread(target=self._pollEncoder, daemon=True)
        self.polling_thread.start()

        logger.info(
            f"Encoder initialized: CLK={clk_pin}, DT={dt_pin}, PPR={pulses_per_revolution}, wheel_diameter={self.wheel_diameter_cm}cm"
        )

    def _pollEncoder(self) -> None:
        time.sleep(0.5)
        self.gc["logger"].info("Encoder polling thread started")

        while True:
            try:
                # Request current encoder position from Arduino via sysex
                self.dev.sysex(0x50, [0x02])  # ENCODER_READ command
                time.sleep(self.gc["encoder_polling_delay_ms"] / 1000.0)
            except Exception as e:
                self.gc["logger"].error(f"Encoder polling error: {e}")
                time.sleep(0.1)

    def _onEncoderResponse(self, *args):
        # Firmata sends each byte as 2 7-bit bytes, so we get 4 bytes total
        # Original data: [low_byte, high_byte] becomes [low_7bits, 0, high_7bits, 0]
        if len(args) >= 4:
            position = args[0] | (args[2] << 7)  # Reconstruct from 7-bit chunks

            if position != self.last_encoder_position:
                pulse_diff = abs(position - self.last_encoder_position)
                with self.lock:
                    self.pulse_count += pulse_diff
                self.last_encoder_position = position

    def getPulseCount(self) -> int:
        with self.lock:
            return self.pulse_count

    def getLastUpdateTime(self) -> float:
        with self.lock:
            return self.last_update_time

    def resetPulseCount(self) -> None:
        with self.lock:
            self.pulse_count = 0
            self.last_update_time = time.time()

    def getPulsesPerRevolution(self) -> int:
        return self.pulses_per_revolution

    def getWheelCircumferenceCm(self) -> float:
        return self.wheel_circumference_cm
