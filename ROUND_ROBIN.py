import simpy
import numpy as np
import numpy.random as random

MAXSIMTIME = 50000
VERBOSE = False
LAMBDA = 3.8
MU = 8.0
POPULATION = 50000000
SERVICE_DISCIPLINE = 'ROUND_ROBIN'
LOGGED = True
PLOTTED = True
TIMESLICE = 0.5

class Job:
    def __init__(self, name, arrtime, duration):
        self.name = name
        self.arrtime = arrtime
        self.duration = duration
        self.alreadyExecute = False

    def __str__(self):
        return '%s at %d, length %d' %(self.name, self.arrtime, self.duration)

class Server:
    def __init__(self, env, strat = 'ROUND_ROBIN'):
        self.env = env
        self.strat = strat
        self.Jobs = list(())
        self.serversleeping = None
        ''' statistics '''
        self.waitingTime = 0
        self.idleTime = 0
        self.jobsDone = 0
        ''' register a new server process '''
        env.process( self.serve() )

    def serve(self):
        while True:
            ''' do nothing, just change server to idle
              and then yield a wait event which takes infinite time
            '''
            if len( self.Jobs ) == 0 :
                self.serversleeping = env.process( self.waiting( self.env ))
                t1 = self.env.now
                yield self.serversleeping
                ''' accumulate the server idle time'''
                self.idleTime += self.env.now - t1
            else:
                ''' get the first job to be served'''
                # self.strat == 'ROUND_ROBIN' by default:
                j = self.Jobs.pop( 0 )
                if (j.duration > TIMESLICE):
                    j.duration -= TIMESLICE
                    ''' sum up the waiting time'''
                    if (j.alreadyExecute == False): #hasn't been executed the first time
                        self.waitingTime += self.env.now - j.arrtime
                    j.alreadyExecute = True
                    self.Jobs.append( j ) 
                    ''' yield an event for the job finish (but not actually finished)'''
                    yield self.env.timeout( TIMESLICE )
                else:
                    ''' sum up the waiting time'''
                    if (j.alreadyExecute == False): #hasn't been executed the first time
                        self.waitingTime += self.env.now - j.arrtime
                    j.alreadyExecute = True
                    ''' sum up the jobs done '''
                    self.jobsDone += 1
                    ''' yield an event for the job finish'''
                    yield self.env.timeout( j.duration )
                if LOGGED:
                    qlog.write( '%.4f\t%d\t%d\n' 
                        % (self.env.now, 1 if len(self.Jobs)>0 else 0, len(self.Jobs)) )
         
    def waiting(self, env):
        try:
            if VERBOSE:
                print( 'Server is idle at %.2f' % self.env.now )
            yield self.env.timeout( MAXSIMTIME )
        except simpy.Interrupt as i:
            if VERBOSE:
                 print('Server waken up and works at %.2f' % self.env.now )

class JobGenerator:
    def __init__(self, env, server, nrjobs = 10000000, lam = 5, mu = 8):
        self.server = server
        self.nrjobs = nrjobs
        self.interarrivaltime = 1/lam;
        self.servicetime = 1/mu;
        env.process( self.generatejobs(env) )
        
    def generatejobs(self, env):
        i = 1
        while True:
            '''yield an event for new job arrival'''
            job_interarrival = random.exponential( self.interarrivaltime )
            yield env.timeout( job_interarrival )

            ''' generate service time and add job to the list'''
            job_duration = random.exponential( self.servicetime )
            self.server.Jobs.append( Job('Job %s' %i, env.now, job_duration) )
            if VERBOSE:
                print( 'job %d: t = %.2f, l = %.2f, dt = %.2f' 
                    %( i, env.now, job_duration, job_interarrival ) )
            i += 1

            ''' if server is idle, wake it up'''
            if not self.server.serversleeping.triggered:
                self.server.serversleeping.interrupt( 'Wake up, please.' )

if LOGGED:
    qlog = open( 'RR_mm1-l%d-m%d.csv' % (LAMBDA,MU), 'w' )
    qlog.write( '0\t0\t0\n' )

env = simpy.Environment()
MyServer = Server( env, SERVICE_DISCIPLINE )
MyJobGenerator = JobGenerator( env, MyServer, POPULATION, LAMBDA, MU )

env.run( until = MAXSIMTIME )

if LOGGED:
    qlog.close()

RHO = LAMBDA/MU
print( 'Arrivals               : %d' % (MyServer.jobsDone) )
print( 'Utilization            : %.2f/%.2f' 
    % (1.0-MyServer.idleTime/MAXSIMTIME, RHO) )
print( 'Mean waiting time      : %.2f/%.2f' 
    % (MyServer.waitingTime/MyServer.jobsDone, RHO**2/((1-RHO)*LAMBDA) ) )

if LOGGED and PLOTTED:
    import matplotlib.pyplot as plt
    log = np.loadtxt( 'RR_mm1-l%d-m%d.csv' % (LAMBDA,MU), delimiter = '\t' )
    plt.subplot( 2, 1, 1 )
    plt.xlabel( 'Time' )
    plt.ylabel( 'Queue length' )
    plt.step( log[:200,0], log[:200,2], where='post' )

    plt.subplot( 2, 1, 2 )
    plt.xlabel( 'Time' )
    plt.ylabel( 'Server state' )
    plt.yticks([0, 1], ['idle', 'busy'])
    #plt.step( log[:200,0], log[:200,1], where='post' )
    plt.fill_between( log[:200,0], 0, log[:200,1], step="post", alpha=.4 )
    plt.tight_layout()
    plt.show()