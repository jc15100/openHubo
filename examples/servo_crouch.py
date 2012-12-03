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
__author__ = 'Robert Ellenberg'
__license__ = 'GPLv3 license'

from openravepy import *
import time
import scipy
import tab
from numpy import *
from numpy.linalg import *
import sys
from servo import *
import openhubo

if __name__=='__main__':

    env = Environment()
    env.SetViewer('qtcoin')
    env.SetDebugLevel(5)

    [robot,controller,ind]=openhubo.load_simplefloor(env)
    print robot
    print controller

    env.StartSimulation(timestep=0.0005)

    robot.GetController().SendCommand('set degrees')

    sendSparseServoCommand(robot,{'LHP':-20,'LKP':40,'LAP':-20,'RHP':-20,'RKP':40,'RAP':-20})

    #Run this in interactive mode to preserve the state

