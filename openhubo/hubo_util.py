import re, copy
import sys
from numpy import pi,array
#import matplotlib.pyplot s plt
#import scipy.spatial as spatial
from openhubo import mapping
import openhubo as oh
import optparse as _optparse

class StateEntry:

    def __init__(self,t=0.0):
        self.t=t
        self.joints={}
        self.sensors={}

    def insert_joint(self,name,data):
        #assumes the type is correct!
        self.joints.setdefault(name,data)

    def insert_sensor(self,name,sensor):
        #assumes the type is correct!
        self.sensors.setdefault(name,sensor)

class StateLog:

    def __init__(self,filename=None):
        self.states=[]
        self.read_from_file(filename)

    def parse(self,raw_line):
        dataorder=['cmd','ref','enc','cur','tmp']
        datalist=re.split('[\t =]+',raw_line)
        #print datalist
        name=datalist[0]
        if mapping.is_ha_joint(name):
            self.states[-1].insert_joint(name,{x:float(y) for x,y in zip(dataorder,datalist[3:12:2])})
        elif re.search('t',datalist[0]):
            try:
                t=float(datalist[1])
                self.states.append(StateEntry(t))
            except ValueError:
                print "time not found in "+datalist[1]

    def read_from_file(self,filename):
        f=open(filename,'r')

        for line in f:
            self.parse(line)

    def slice_states(self,name,field):
        return [s.joints[name][field] for s in self.states]

    def write_joint_pair(self,j0,j1,destname='out.pair'):
        sl0=array(self.slice_states(j0,2))
        sl1=array(self.slice_states(j1,2))
        with open(destname,'w') as f:
            for p1,p2 in zip(sl0,sl1):
                f.write('{},{}\n'.format(p1,p2))

class JointTable:
    def __init__(self,filename=None):
        self.joints={}
        self.read_from_file(filename)

    def parse(self,raw_line):
        dataorder=['name','motNo','refEnc','drive','driven','harm','enc','dir','jmc','active','can','numMot','zeroed']
        datalist=re.split('[\t =]+',raw_line.rstrip())
        print datalist
        name=datalist[0]
        if mapping.is_ha_joint(name):
            joint = {x:int(y) if not re.search('[JE]',y[0]) else y for x,y in zip(dataorder[1:],datalist[1:])}
            self.joints[name]=joint

    def read_from_file(self,filename):
        f=open(filename,'r')

        for line in f:
            self.parse(line)

    def get_ratio(self,joint):
        drive=self.joints[joint]['drive']
        driven=self.joints[joint]['driven']
        harm=self.joints[joint]['harm']
        #NOTE: drive/driven seems backwards, but the output is wrong otherwise
        return float(harm)*driven/drive

    def rad_from_ticks(self,joint,value):
        ratio=self.get_ratio(joint)
        enc=self.joints[joint]['enc']
        return value/ratio/enc*2*pi

    def ticks_from_rad(self,joint,value):
        ratio=self.get_ratio(joint)
        enc=self.joints[joint]['enc']
        return value*ratio*enc/2/pi


class LimitTable:
    dataorder=['JointName','HomeOffset','LowerLimit','UpperLimit','SearchDirection','SearchLimit','Type']
    def __init__(self,filename=None):
        self.joints={}
        self.read_from_file(filename)

    def parse(self,raw_line):

        datalist=re.split('[\t =]+',raw_line.rstrip())
        print datalist
        name=datalist[0]
        if mapping.is_ha_joint(name):
            joint = {x:int(y) if not re.search('r',y[0]) else y for x,y in zip(self.dataorder[1:],datalist[1:])}
            self.joints[name]=joint

    def read_from_file(self,filename):
        f=open(filename,'r')
        print "Reading from file {}...".format(filename)

        for line in f:
            self.parse(line)
        print "Done reading from file {}...".format(filename)

    def shift_home(self,joint,ticks):
        oldhome=self.joints[joint]['HomeOffset']
        self.joints[joint]['HomeOffset']+=ticks
        self.joints[joint]['LowerLimit']+=ticks
        self.joints[joint]['UpperLimit']+=ticks
        print "{} home changed from {} to {} ticks".format(joint,oldhome,self.joints[joint]['HomeOffset'])
        return self.joints[joint]['HomeOffset']

    def write_to_file(self,filename):
        with open(filename,'w') as f:
            f.write('# This table was automatically generated by python code... \n')
            f.write('# The values in this table are based on the homing\n')
            f.write('# parameters on the hardware at the time that the function was run.\n')
            f.write('\n')
            f.write('# -- Units in this table are in terms of encoder values (raw)\n')
            f.write('\n')
            f.write('JointName   HomeOffset  LowerLimit  UpperLimit  SearchDirection SearchLimit Type\n')
            for name,j in self.joints.items():
                datalist=[name]
                datalist.extend([str(j[x]) for x in self.dataorder[1:]])
                datalist.append('\n')
                f.write(' '.join(datalist))


class LimitProcessor:
    def __init__(self,joint_table_file,limit_table_file,log_file=None):
        self.joint_table=JointTable(joint_table_file)
        self.limit_table=LimitTable(limit_table_file)
        self.old_limit_table=copy.deepcopy(self.limit_table)
        if log_file is not None:
            self.hubo_log=StateLog(log_file)
        else:
            self.hubo_log=None

    def adjust_limit_from_rad(self,joint,rads):
        ticks=int(self.joint_table.ticks_from_rad(joint,rads))
        return self.limit_table.shift_home(joint,ticks)

    def adjust_limits_from_log(self,jointnames=None):
        """Based on the log file read and the specified joint names, offset the home positions and limits"""
        if jointnames is None:
            #Assume any changed refs are new home position settings
            for n in self.limit_table.joints.keys():
                if abs(self.hubo_log.states[-1].joints[n]['ref'])>0:
                    self.adjust_limit_from_rad(n,self.hubo_log.states[-1].joints[n]['ref'])

        for n in jointnames:
            if self.limit_table.joints.has_key(n):
                #Using REF position here instead of encoder, since the joints sag under body weight
                self.adjust_limit_from_rad(n,self.hubo_log.states[-1].joints[n]['ref'])

    def get_rad_limits(self):
        """Return maps of lower and upper limits with respect to home position"""
        lower={}
        upper={}
        for name,data in self.limit_table.joints.items():
            lower[name]=self.joint_table.rad_from_ticks(name,data['LowerLimit'])
            upper[name]=self.joint_table.rad_from_ticks(name,data['UpperLimit'])
        return (lower,upper)

    def apply_limits_to_model(self,robot):
        (lower,upper)=self.get_rad_limits()

        for name in self.limit_table.joints.keys():
            n=mapping.oh_from_ha(name)
            j=robot.GetJoint(n)
            if j is not None:
                j.SetLimits([lower[name]],[upper[name]])

def _setup():
    parser = _optparse.OptionParser(description='Hubo Home Position utility. Uses a hubo-read log file as the new reference pose, and stores updated offsets to the robot',
                                    usage='usage: %prog [options] script')

    parser.add_option('--logfile', action="store",type='string',dest='logfile',default=None,
                             help='Hubo Log file')

    adjuster=LimitProcessor(joint_table_file,limit_table_file,log_file)

    parser.add_option('--limit-table', action="store",type='string',dest='limit_table',default=None,
                             help='Limit table (*.table)')

    return parser.parse_args()


def run():
    (options,leftargs)=_setup()
    updater=LimitProcessor(options.joint_table,options.limit_table,options.logfile)
    return updater

if __name__=='__main__':
    from openhubo import startup
    joint_table_file=sys.argv[1]
    limit_table_file=sys.argv[2]
    if len(sys.argv)>3:
        log_file=sys.argv[3]
    else:
        log_file=None

    updater=LimitProcessor(joint_table_file,limit_table_file,log_file)
