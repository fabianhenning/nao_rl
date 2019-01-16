
"""
@author: Andrius Bernatavicius, 2018
"""
from __future__ import print_function
import time, math
import numpy as np
import cv2 as cv
from gym import spaces


# Local imports
from nao_rl.environments import VrepEnv
from nao_rl.utils import RealNAO, VrepNAO, Ball, image_processing
from nao_rl import settings


class NaoTracking(VrepEnv):
    """ 
    Environment where the goal is to track the ball by moving two head motors.
    The ball moves randomly within a specified area and the reward is proportional to the distance from
    the center of the ball to the center of NAO's vision sensor.
    """
    def __init__(self, address=None, port=None, naoqi_port=None, window=None, real=False):

        if port is None:
            port = settings.SIM_PORT
        if address is None:
            address = settings.LOCAL_IP
        VrepEnv.__init__(self, address, port)

        # Vrep
        self.window = window
        self.path = settings.SCENES + '/nao_ball.ttt'

        # Objects
        self.ball  = Ball(name='Sphere1')

        if real:
            self.agent = RealNao(settings.REAL_NAO_IP, settings.NAO_PORT)
        else:
            self.agent = VrepNAO(True)

        
        self.active_joints = ['Head']
        self.body_parts = ['Head']
        

        # Action and state spaces
        # self.velocities = [0, 0]
        # self.velocity_bounds = [-.02, .02]
        self.action_space = spaces.Box(low=np.array([-1, -1]),
                                       high=np.array([1, 1]),
                                       dtype=np.float32)

        self.observation_space = spaces.Box(low=np.array([-np.inf] * 4),
                                            high=np.array([np.inf] * 4),
                                            dtype=np.float32)
        self.state = np.zeros(14)

        # Simulations parameters
        self.done = True
        self.steps = 0


    def initialize(self):
        """
        Connects to vrep, loads the scene and initializes the posture of NAO
        """
        self.connect()
        self.agent.connect(self)
        

        # Window for displaying the camera image
        # if self.window is not None:
        #     cv.namedWindow(self.window, cv.WINDOW_NORMAL)
        #     cv.resizeWindow('s', 600,600)


    def _make_observation(self):
        """
        Make an observation: obtain an image from the virtual sensor
        State space - [normalized coordinates of the center of the ball [0-1], 
                       velocities of the head motors]
        """
        image, resolution = self.agent.get_image(mode='buffer')

        angles = self.agent.get_angles()
        _, center, resolution = image_processing.ball_tracking(image, resolution, self.window)

        if center != None:
            
            coords = [float(center[x])/float(resolution[x]) for x in range(2)]
            self.state = [coords[0], coords[1], angles[0], angles[1]]
        else:
            self.done = True
            self.state = [0, 0, angles[0], angles[1]]
        
        

    def _make_action(self, action):
        """
        Perform and action: increase the velocity of either 'HeadPitch' or 'HeadYaw'
        """

        # Update velocities
        # for i in range(len(self.velocities)):
        #     self.velocities[i] += action[i] / 1000
        #     if self.velocities[i] < self.velocity_bounds[0]: self.velocities[i] = self.velocity_bounds[0]
        #     if self.velocities[i] > self.velocity_bounds[1]: self.velocities[i] = self.velocity_bounds[1]

        self.agent.move_joints(action/20)


    def step(self, action):
        """
        Step the vrep simulation by one frame
        """
        self.steps += 1
        self._make_action(action)
        self.step_simulation()
        self._make_observation()
        # self.ball.random_motion()
        (center_x, center_y, _, _) = self.state

        # Euclidean distance from the center of the ball
        reward = 1. - np.sqrt((0.5 - center_x)**2 + (0.5 - center_y)**2)
        # if center_x > .8 or center_x < .2 or center_y < 0.2 or center_y > .8:
        #     reward = 0
        #if self.done:
            #reward = -1/self.steps * 200

        return np.array(self.state), reward, self.done, {}

    def reset(self, close=False):
        """
        Reset the environment to default state and return the first observation
        """ 
        # Reset state
        self.get_vision_image(self.agent.camera_handle, 'streaming') # Start streaming
        self.steps = 0
        self.velocities = [0, 0]
        self.state = []
        self.done = False

        self.stop_simulation()
        self.agent.reset_position()
        self.start_simulation()
        self.state = np.zeros(4)
        self.step_simulation()
        self._make_observation()
        return np.array(self.state)

    def run(self):
        """
        Run the test simulation without any learning algorithm for debugging purposes
        """
        self.reset()
        t = 0
        while t < 10:
            self.done = False
            self.start_simulation()
            while not self.done:
                raw_input("Press Enter to continue...")
                action = self.action_space.sample()
                print(action)
                state, reward, self.done, _ = self.step(action)
                print('Current state:\n angles: {}'.format(state))
                print('Reward: {}'.format(reward))

            self.stop_simulation()
            t += 1


if __name__ == "__main__":

    """
    If called as a script this will initialize the scene in an open vrep instance 
    """
    import nao_rl
    env = nao_rl.make('NaoTracking', headless=False)
    env.run()