#!/usr/bin/env python
#// This program is free software: you can redistribute it and/or modify
#// it under the terms of the GNU Lesser General Public License as published by
#// the Free Software Foundation, either version 3 of the License, or
#// at your option) any later version.
#//
#// This program is distributed in the hope that it will be useful,
#// but WITHOUT ANY WARRANTY; without even the implied warranty of
#// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#// GNU Lesser General Public License for more details.
#//
#// You should have received a copy of the GNU Lesser General Public License
#// along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement # for python 2.5
__author__ = 'Juan Gonzalez'
__copyright__ = 'Copyright (C) 2010 Juan Gonzalez (juan@iearobotics.com)'
__license__ = 'GPLv3 license'

#-- This is an example for testing the servocontroller located in the
#-- Modular Robot Open Rave plugin
#-- The two servos of the Minicube-I modular robot are both set to 45
#-- and -45 degrees.
#-- The Minicube-I modular robot is composed of two Y1 modules.


from openravepy import *
from numpy import *
import time
import datetime
import sys

def trans(T,x,y,z):
    T[0,3]=x; T[1,3]=y; T[2,3]=z;
    return T

def run():

    #-- Read the name of the xml file passed as an argument
    #-- or use the default name
    try:
        file_env = sys.argv[1]
    except IndexError:
        file_env = 'simpleFloor.env.xml'

    env = Environment()
    env.SetViewer('qtcoin')
    env.SetDebugLevel(5)
    env.Load(file_env)

    #-- Set the robot controller and start the simulation
    with env:
        robot = env.GetRobots()[0]
        robot.SetController(RaveCreateController(env,'servocontroller'))
        collisionChecker = RaveCreateCollisionChecker(env,'bullet')
        env.SetCollisionChecker(collisionChecker)

        #define ODE physics engine and set gravity
        #physics = RaveCreatePhysicsEngine(env,'ode')
        #physics.SetGravity([0,0,0])
        #env.SetPhysicsEngine(physics)

        env.StopSimulation()
        env.StartSimulation(timestep=0.001)

    robot.GetController().SendCommand('setpos1 4 10 ')
    time.sleep(1)

    robot.GetController().SendCommand('setgains 8.3 0 1 .90 .6')
    robot.GetController().SendCommand("record_on")

    robot.GetController().SendCommand('setpos1 6 -60 ')
    time.sleep(5.0)
    filename="servodata_{}.txt".format(datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
    robot.GetController().SendCommand("record_off {} 6".format(filename))

if __name__=='__main__':
    run()


