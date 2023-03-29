from robot.irl.motors import PCA9685, Servo, Stepper
from robot.irl.bins import DistributionModule, Bin

#will package this as a .json once there's a UI
config = {
    "mc_path": "/dev/ttyACM0",
    "distribution_modules": [
        {
            "distance_from_camera": 20, #cm
            "num_bins": 4,
            "controller_address": 0x40,
        },
        {
            "distance_from_camera": 30,
            "num_bins": 4,
            "controller_address": 0x41,
        },
        {
            "distance_from_camera": 40,
            "num_bins": 4,
            "controller_address": 0x42,
        },
    ],
    "feeder_stepper": {
        "dir_pin": 2,
        "step_pin": 3,
        "microstepping": 1
        "steps_per_second": 25,
    },
    "main_conveyor_stepper": {
        "dir_pin": 4,
        "step_pin": 6,
        "microstepping": 1
        "steps_per_second": 25,
    },
}

def buildConfig(config=config):
    mc = Arduino(config["mc_path"])
    it = util.Iterator(mc)
    it.start()
    def messageHandler(*args, **kwargs):
        print(util.two_byte_iter_to_str(args))
    dev.add_cmd_handler(pyfirmata.STRING_DATA, messageHandler)

    fs = Stepper(config["feeder_stepper"]["dir_pin"], config["feeder_stepper"]["step_pin"], config["feeder_stepper"]["microstepping"], dev, config["feeder_stepper"]["steps_per_second"])
    cs = Stepper(config["main_conveyor_stepper"]["dir_pin"], config["main_conveyor_stepper"]["step_pin"], config["main_conveyor_stepper"]["microstepping"], dev, config["main_conveyor_stepper"]["steps_per_second"])
    
    dms = []
    for dm in config["distribution_modules"]:
        servo_controller = PCA9685(dm["controller_address"])
        chute_servo = Servo(15, servo_controller)
        bins = [Bin(Servo(i, servo_controller)) for i in range(dm["num_bins"])]
        dms.append(DistributionModule(chute_servo, dm["distance_from_camera"], bins))

    return (mc, dms, cs, fs)
