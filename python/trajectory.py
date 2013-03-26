#!/usr/bin/env python
from openravepy import *
from servo import *
from numpy import pi
import re
import openhubo 
from TransformMatrix import *
from rodrigues import *

def create_trajectory(robot):
    """ Create a trajectory based on a robot's config spec"""
    traj=RaveCreateTrajectory(robot.GetEnv(),'')
    config=robot.GetConfigurationSpecification()
    config.AddDeltaTimeGroup()
    traj.Init(config)
    return [traj,config]

def read_youngbum_traj(filename,robot,dt=.01,scale=1.0,retime=True):
    """ Read in trajectory data stored in Youngbum's format (100Hz data):
        HPY LHY LHR ... RWP   (3-letter names)
        + - + ... +           (sign of joint about equivalent global axis + / -)
        0.0 5.0 2.0 ... -2.0  (Offset of joint from openHubo "zero" in YOUR sign convention)
        (data by row, single space separated)
    """
    #TODO: handle multiple spaces
    #Setup trajectory and source file
    traj=RaveCreateTrajectory(robot.GetEnv(),'')
    config=robot.GetConfigurationSpecification()
    config.AddDeltaTimeGroup()
    traj.Init(config)
    ind=openhubo.makeNameToIndexConverter(robot)
    #Affine DOF are not controlled, so fill with zeros
    affinedof=zeros(7) 

    f=open(filename,'r')

    #Read in header row to find joint names
    header=f.readline().rstrip()
    print header.split(' ')

    indices=[ind(s) for s in header.split(' ')]

    #Read in sign row
    signlist=f.readline().rstrip().split(' ')
    signs=[]
    print signlist
    for s in signlist:
        if s == '+':
            signs.append(1)
        else:
            signs.append(-1)
    
    #Read in offset row (fill with zeros if not used)
    offsetlist=f.readline().rstrip().split(' ')
    print offsetlist
    offsets=[float(x) for x in offsetlist]

    k=0
    while True: 
        string=f.readline().rstrip()
        if len(string)==0:
            break
        jointvals=[float(x) for x in string.split(' ')]
        data=zeros(robot.GetDOF())

        for i in range(len(jointvals)):
            data[indices[i]]=(jointvals[i]+offsets[i])*pi/180.0*signs[i]*scale
        #TODO: clip joint vals at limits

        waypt=list(data)
        waypt.extend(affinedof)
        waypt.append(dt)
        traj.Insert(k,waypt)
        k=k+1
    if retime:
        planningutils.RetimeActiveDOFTrajectory(traj,robot,True)

    return traj

def write_youngbum_traj(traj,robot,dt,filename='exported.traj',dofs=None,oldnames=False):
    """ Create a text trajectory in youngbum's style, assuming no offsets or
    scaling, and openHubo default sign convention.
    """
    config=robot.GetConfigurationSpecification()
    ind=openhubo.makeNameToIndexConverter(robot)

    f=open(filename,'w')

    namelist=[]
    signlist=[]
    scalelist=[]
    offsetlist=[]

    if dofs is None:
        dofs=range(robot.GetDOF())
    for d in dofs:
        name=robot.GetJointFromDOFIndex(d).GetName()
        if oldnames:
            namelist.append(openhubo.get_huboname_from_name(name))
        else:
            namelist.append(name)
        #TODO make this an argument?
        signlist.append('+')
        offsetlist.append(0.0)
        scalelist.append(1.0)

    #Find overall trajectory properties
    T=traj.GetDuration()
    steps=int(T/dt)
    
    with  open(filename,'w') as f:
        f.write(' '.join(namelist)+'\n')
        f.write(' '.join(signlist)+'\n')
        f.write(' '.join(['{}'.format(x) for x in offsetlist])+'\n')
        f.write(' '.join(['{}'.format(x) for x in scalelist])+'\n')

        for t in arange(0,T,dt):
            waypt=traj.Sample(t)
            vals=config.ExtractJointValues(waypt,robot,dofs)
            f.write(' '.join(['{}'.format(x) for x in vals])+'\n')

def write_hubo_traj(traj,robot,dt,filename='exported.traj'):
    """ Create a text trajectory for reading into hubo-read-trajectory."""
    config=robot.GetConfigurationSpecification()
    ind=openhubo.makeNameToIndexConverter(robot)

    f=open(filename,'w')


    #Find overall trajectory properties
    T=traj.GetDuration()
    steps=int(T/dt)
   
    #Get all the DOF's..
    dofs = range(robot.GetDOF())
    with open(filename,'w') as f:
        for t in arange(0,T,dt):
            waypt=traj.Sample(t)
            #Extract DOF values
            vals=config.ExtractJointValues(waypt,robot,dofs)
            #start with array of zeros size of hubo-ach trajectory width
            mapped_vals=zeros(max(openhubo.hubo_map.values()))
            for d in dofs:
                n = robot.GetJointFromDOFIndex(d).GetName()
                if openhubo.hubo_map.has_key(n):
                    mapped_vals[openhubo.hubo_map[n]]=vals[d]
            f.write(' '.join(['{}'.format(x) for x in mapped_vals])+'\n')

def read_text_traj(filename,robot,dt=.01,scale=1.0):
    """ Read in trajectory data stored in Youngbum's format (100Hz data):
        HPY LHY LHR ... RWP   (3-letter names)
        + - + ... +           (sign of joint about equivalent global axis + / -)
        0.0 5.0 2.0 ... -2.0  (Offset of joint from openHubo "zero" in YOUR sign
        convention and scale)
        1000 1000 pi/180 pi/180 ... pi/180 (scale of your units wrt openrave
        default)
        (data by row, single space separated)
    """
    #TODO: handle multiple spaces
    #Setup trajectory and source file
    traj=RaveCreateTrajectory(robot.GetEnv(),'')
    config=robot.GetConfigurationSpecification()
    config.AddDeltaTimeGroup()
    traj.Init(config)
    ind=openhubo.makeNameToIndexConverter(robot)
    #Affine DOF are not controlled, so fill with zeros
    affinedof=zeros(7) 

    f=open(filename,'r')

    #Read in header row to find joint names
    header=f.readline().rstrip()
    #print header.split(' ')
    
    k=0
    indices={}
    Tindices={}
    Tmap={'X':0,'Y':1,'Z':2,'R':3,'P':4,'W':5}
    for s in header.split(' '):
        j=ind(s)
        if j>=0:
            indices.setdefault(k,j)
        try:
            Tindices.setdefault(k,Tmap[s])
        except KeyError:
            pass
        except:
            raise
        k=k+1
    #Read in sign row
    signlist=f.readline().rstrip().split(' ')
    signs=[]
    for s in signlist:
        if s == '+':
            signs.append(1)
        else:
            signs.append(-1)
    
    #Read in offset row (fill with zeros if not used)
    offsetlist=f.readline().rstrip().split(' ')
    offsets=[float(x) for x in offsetlist]
    #Read in scale row (fill with ones if not used)
    scalelist=f.readline().rstrip().split(' ')
    scales=[float(x) for x in scalelist]

    k=0
    while True: 
        string=f.readline().rstrip()
        if len(string)==0:
            break
        vals=[float(x) for x in string.split(' ')]
        data=zeros(robot.GetDOF())
        Tdata=zeros(6)
        for i in range(len(vals)):
            if indices.has_key(i):
                data[indices[i]]=(vals[i]+offsets[i])*scales[i]*signs[i]*scale
            elif Tindices.has_key(i):
                Tdata[Tindices[i]]=(vals[i]+offsets[i])*scales[i]*signs[i]*scale
        #TODO: clip joint vals at limits
        T=MakeTransform(rodrigues(Tdata[3:]),mat(Tdata[0:3]).T)
        waypt=list(data)
        #Assume full affine control 
        waypt.extend(poseFromMatrix(array(T)))
        waypt.append(dt)
        traj.Insert(k,waypt)
        k=k+1

    return traj

def makeJointValueExtractor(robot,traj,config):
    """Closure to pull a full body pose out of a trajectory waypoint"""
    def GetJointValuesFromWaypoint(index):
        return config.ExtractJointValues(traj.GetWaypoint(index),robot,range(robot.GetDOF()))
    return GetJointValuesFromWaypoint

def makeTransformExtractor(robot,traj,config):
    """Closure to pull a transform out of a trajectory waypoint"""
    v=poseFromMatrix(eye(4))
    def GetTransformFromWaypoint(index):
        #Ugly way to extract transform because the ExtractAffineValues function
        #is not yet bound 
        return matrixFromPose(traj.GetWaypoint(index)[-8:-1])
    return GetTransformFromWaypoint

if __name__=='__main__':
    from recorder import viewerrecorder

    try:
        traj_name = sys.argv[1]
    except IndexError:
        traj_name = 'trajectories/pump_reach.traj.txt'

    env = Environment()
    (env,options)=openhubo.setup('qtcoin')
    env.SetDebugLevel(4)

    timestep=0.0005

    #-- Set the robot controller and start the simulation
    robot=openhubo.load_simplefloor(env)
    ind=openhubo.makeNameToIndexConverter(robot)
    controller=robot.GetController()

    env.StartSimulation(timestep=timestep)

    #The name-to-index closure makes it easy to index by name 
    # (though a bit more expensive)
    traj=read_youngbum_traj(traj_name,robot,.015,.9)

    vidrec=viewerrecorder(env)
    controller.SetPath(traj)
    vidrec.start()
    controller.SendCommand('start')
    while not(controller.IsDone()):
        time.sleep(.1)
        print controller.GetTime()
    vidrec.stop()

