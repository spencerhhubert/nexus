# BrickLink module initialization
# This module handles BrickLink API integration for piece data generation and management

from robot.piece.bricklink.auth import mkAuth
from robot.piece.bricklink.generate import generateBricklinkData
from robot.piece.bricklink.generate_categories import generateCategories
from robot.piece.bricklink.generate_colors import generateColors
from robot.piece.bricklink.generate_kinds import generateKinds
