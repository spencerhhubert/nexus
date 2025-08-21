import sys
import time
import threading
from robot.global_config import buildGlobalConfig
from robot.irl.config import buildIRLConfig, buildIRLSystemInterface


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_motors.py <motor_name> [initial_speed]")
        print("Available motors:")
        print("  main_conveyor")
        print("  feeder_conveyor")
        print("  first_vibration_hopper")
        print("  second_vibration_hopper")
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
    if len(our_args) > 1:
        try:
            speed = int(our_args[1])
        except ValueError:
            print(f"Invalid speed value: {our_args[1]}")
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
    if speed is None:
        speed = gc[speed_key]

    print(f"Connecting to {motor_name} motor...")

    irl_config = buildIRLConfig()
    irl_system = buildIRLSystemInterface(irl_config, gc)
    motor = irl_system[motor_key]

    current_speed = 0
    running = True

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
                    motor.setSpeed(current_speed)
                    print(f"Motor speed set to: {current_speed}")
                except ValueError:
                    print("Invalid input. Enter a number (-255 to 255) or 'q' to quit.")
            except (EOFError, KeyboardInterrupt):
                running = False
                break

    try:
        print(f"\nMotor: {motor_name}")
        print(f"Default speed: {gc[speed_key]}")
        print(f"Initial speed: {speed}")
        print("\nEnter new speed values (-255 to 255) or 'q' to quit:")

        current_speed = speed
        motor.setSpeed(current_speed)
        print(f"Motor speed: {current_speed}")

        # Start input thread
        input_handler = threading.Thread(target=input_thread, daemon=True)
        input_handler.start()

        # Main loop - just keep the program alive
        while running:
            time.sleep(0.1)

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
