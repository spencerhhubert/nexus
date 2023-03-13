from pyfirmata import Arduino
import irl.motors

feeder_stepper_dir_pin = 2
feeder_stepper_step_pin = 3
main_conveyor_stepper_dir_pin = 4
main_conveyor_stepper_step_pin = 5

if __name__ == "__main__":
    dev = Arduino('/dev/ttyACM0')
    feeder_stepper = irl.motors.Stepper(feeder_stepper_dir_pin, feeder_stepper_step_pin, 200*16, dev)
    main_conveyor_stepper = irl.motors.Stepper(main_conveyor_stepper_dir_pin, main_conveyor_stepper_step_pin, 200*16, dev)
    feeder_stepper.run(True, 5000)
    main_conveyor_stepper.run(True, 5000)




