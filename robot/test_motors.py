import sys
import time
import threading
from robot.global_config import buildGlobalConfig
from robot.irl.config import buildIRLConfig, buildIRLSystemInterface

PULSE_ON_TIME_MS = 200
PULSE_OFF_TIME_MS = 200


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_motors.py <motor_name> [initial_speed] [--no-pulse]")
        print("Available motors:")
        print("  main_conveyor")
        print("  feeder_conveyor")
        print("  first_vibration_hopper")
        print("  second_vibration_hopper")
        print("Options:")
        print("  --no-pulse    Run motor continuously without pulsing")
        sys.exit(1)

    motor_name = sys.argv[1]

    # Store our args and clear sys.argv so buildGlobalConfig doesn't see them
    our_args = sys.argv[1:]
    sys.argv = [sys.argv[0]]

    # Build config with minimal logging to avoid cluttering interactive mode
    gc = buildGlobalConfig()
    gc["debug_level"] = 0  # Reduce log verbosity
    logger = gc["logger"]

    speed = None
    no_pulse = False

    # Parse arguments
    for arg in our_args[1:]:
        if arg == "--no-pulse":
            no_pulse = True
        elif speed is None:
            try:
                speed = int(arg)
            except ValueError:
                print(f"Invalid speed value: {arg}")
                sys.exit(1)

    motor_map = {
        "main_conveyor": ("main_conveyor_dc_motor", "main_conveyor_speed"),
        "feeder_conveyor": ("feeder_conveyor_dc_motor", "feeder_conveyor_speed"),
        "first_vibration_hopper": (
            "first_vibration_hopper_motor",
            "first_vibration_hopper_motor_speed",
        ),
        "second_vibration_hopper": (
            "second_vibration_hopper_motor",
            "second_vibration_hopper_motor_speed",
        ),
    }

    if motor_name not in motor_map:
        print(f"Unknown motor: {motor_name}")
        print("Available motors: " + ", ".join(motor_map.keys()))
        sys.exit(1)

    motor_key, speed_key = motor_map[motor_name]

    print(f"Connecting to {motor_name} motor...")

    irl_config = buildIRLConfig()
    irl_system = buildIRLSystemInterface(irl_config, gc)
    motor = irl_system[motor_key]

    if speed is None:
        speed = irl_system["runtime_params"][speed_key]

    current_speed = 0
    running = True
    pulse_state = True  # True = motor on, False = motor off
    last_pulse_time = time.time()
    motor_is_running = False  # Track actual motor state
    last_set_speed = None  # Track the last speed we set

    def input_thread():
        nonlocal current_speed, running
        while running:
            try:
                user_input = input().strip()
                if user_input.lower() in ["q", "quit", "exit"]:
                    running = False
                    break
                try:
                    new_speed = int(user_input)
                    current_speed = new_speed
                    print(f"Motor speed set to: {current_speed}")
                except ValueError:
                    print("Invalid input. Enter a number (-255 to 255) or 'q' to quit.")
            except (EOFError, KeyboardInterrupt):
                running = False
                break

    try:
        print(f"\nMotor: {motor_name}")
        print(f"Default speed: {irl_system['runtime_params'][speed_key]}")
        print(f"Initial speed: {speed}")
        if no_pulse:
            print("Mode: Continuous (no pulsing)")
        else:
            print(f"Pulse timing: {PULSE_ON_TIME_MS}ms on, {PULSE_OFF_TIME_MS}ms off")
        print("\nEnter new speed values (-255 to 255) or 'q' to quit:")

        current_speed = speed

        # Start input thread
        input_handler = threading.Thread(target=input_thread, daemon=True)
        input_handler.start()

        if no_pulse:
            # Continuous mode - just maintain motor speed
            motor.setSpeed(current_speed)
            print(f"Motor running continuously at speed {current_speed}")

            while running:
                if last_set_speed != current_speed:
                    motor.setSpeed(current_speed)
                    last_set_speed = current_speed
                    print(f"Motor speed changed to {current_speed}")
                time.sleep(0.01)
        else:
            # Main pulsing loop
            while running:
                current_time = time.time()

                if pulse_state:
                    # Motor should be on, check if it's time to turn off
                    if (current_time - last_pulse_time) * 1000 >= PULSE_ON_TIME_MS:
                        if motor_is_running:
                            motor.setSpeed(0)
                            motor_is_running = False
                            last_set_speed = 0
                        pulse_state = False
                        last_pulse_time = current_time
                        print("Motor OFF")
                    else:
                        # Ensure motor is running at correct speed if not already
                        if not motor_is_running or last_set_speed != current_speed:
                            motor.setSpeed(current_speed)
                            motor_is_running = True
                            last_set_speed = current_speed
                else:
                    # Motor should be off, check if it's time to turn on
                    if (current_time - last_pulse_time) * 1000 >= PULSE_OFF_TIME_MS:
                        motor.setSpeed(current_speed)
                        motor_is_running = True
                        last_set_speed = current_speed
                        pulse_state = True
                        last_pulse_time = current_time
                        print(f"Motor ON at speed {current_speed}")

                time.sleep(0.01)  # Small sleep to prevent excessive CPU usage

    except KeyboardInterrupt:
        running = False
    finally:
        print("\nStopping motor...")
        motor.setSpeed(0)
        irl_system["arduino"].flush()
        irl_system["arduino"].close()
        print("Test complete")


if __name__ == "__main__":
    main()
