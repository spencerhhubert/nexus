from pyfirmata import Arduino
import robot.sort as s
from robot.classification.profile import Profile

if __name__ == "__main__":
    profile = Profile("/nexus/databases/pieces.db")
    s.sort(profile)
