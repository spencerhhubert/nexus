import time
from robot.irl.config import buildIRLSystemInterface, IRLSystemInterface, buildIRLConfig
from robot.irl.motors import Servo
from robot.global_config import GlobalConfig, buildGlobalConfig

def sweep_servo(servo: Servo, start_angle: int, end_angle: int, step: int, delay_ms: int) -> None:
    current_angle = start_angle
    direction = 1 if end_angle > start_angle else -1
    step = abs(step) * direction

    while (direction > 0 and current_angle <= end_angle) or (direction < 0 and current_angle >= end_angle):
        servo.setAngle(current_angle)
        time.sleep(delay_ms / 1000)
        current_angle += step

def run_sweep_demo() -> None:
    global_config = buildGlobalConfig()
    irl_config = buildIRLConfig()
    system: IRLSystemInterface = buildIRLSystemInterface(irl_config, global_config)
    mc, dms = system

    debug_level = global_config["debug_level"]
    if debug_level > 0:
        print(f"Running with debug level: {debug_level}")

    try:
        while True:
            # Skip the first dm, start from the second one (index 1)
            for dm_idx, dm in enumerate(dms):
                if dm_idx == 0:
                    continue  # Skip the first distribution module

                if debug_level > 0:
                    print(f"Sweeping distribution module {dm_idx}")

                sweep_servo(dm.servo, 90, 135, 5, 100)
                sweep_servo(dm.servo, 135, 90, 5, 100)

                for bin_idx, bin in enumerate(dm.bins):
                    if debug_level > 0:
                        print(f"Sweeping bin {bin_idx} in module {dm_idx}")

                    sweep_servo(bin.servo, 170, 135, 5, 100)
                    sweep_servo(bin.servo, 135, 170, 5, 100)

            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping servo demo")
        for dm in dms:
            dm.servo.setAngle(90)
            for bin in dm.bins:
                bin.servo.setAngle(170)

if __name__ == "__main__":
    run_sweep_demo()
