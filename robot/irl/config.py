from robot.irl import motors

#somewhat temp, would like to make a json config file parser. will wait unitl there's a good UI
def buildConfig():
    mc_path = "/dev/ttyACM0"
    mc = Arduino(mc_path)

    it = util.Iterator(mc)
    it.start()
    def messageHandler(*args, **kwargs):
        print(util.two_byte_iter_to_str(args))
    dev.add_cmd_handler(pyfirmata.STRING_DATA, messageHandler)

    feeder_stepper_dir_pin = 2
    feeder_stepper_step_pin = 3
    main_conveyor_stepper_dir_pin = 4
    main_conveyor_stepper_step_pin = 6 #pin 5 seems to have interference problem. might try capacitor?

    fs = irl.motors.Stepper(feeder_stepper_dir_pin, feeder_stepper_step_pin, 1, dev, 0)
    cs = irl.motors.Stepper(main_conveyor_stepper_dir_pin, main_conveyor_stepper_step_pin, 1, dev, 1)

    dms = [] #distribution modules

    dm_bins1 = []
    servo_controller1 = PCA9685(mc, 0x40)
    for bin in range(0,4): #each has four bins right now, can expand to eight
        dm_bins1.append(Servo(bin, servo_controller1))
    dm_bins1.append(Servo(15, servo_controller1)) #chute door
    dms.append(dm_bins1)

    dm_bins2 = []
    servo_controller2 = PCA9685(mc, 0x41)
    for bin in range(0,4):
        dm_bins2.append(Servo(bin, servo_controller2))
    dm_bins2.append(Servo(15, servo_controller2))
    dms.append(dm_bins2)

    dm_bins3 = []
    servo_controller3 = PCA9685(mc, 0x42)
    for bin in range(0,4):
        dm_bins3.append(Servo(bin, servo_controller3))
    dm_bins3.append(Servo(15, servo_controller3))
    dms.append(dm_bins3)

    return (mc, dms, cs, fs)
