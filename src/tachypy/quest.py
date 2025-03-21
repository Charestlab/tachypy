#!/usr/bin/env python

# Copyright (c) 1996-2002 Denis G. Pelli
# Copyright (c) 1996-9 David Brainard
# Copyright (c) 2004-7 Andrew D. Straw
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   a. Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#   b. Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#   c. Neither the name of the Enthought nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.

__all__ = ['QuestObject']

import math
import copy
import warnings
import random
import sys
import time
import numpy as np

def getinf(x):
    return np.nonzero( np.isinf( np.atleast_1d(x) ) )


def alt_round(x):
    """
     alt_round(x)
     
     <x> is an array
     
     simulate the rounding behavior of matlab where 0.5 rounds 
     to 1 and -.5 rounds to -1. (python rounds ties to the
     nearest even integer.)
     
     return:
      an array of rounded values (as integers)
    
     example:
     import numpy as np
     x = np.array([-1, -0.5, 0, 0.5, 0.7, 1.0, 1.5, 2.1, 2.5, 2.6, 3.5])
     y = alt_round(x)

    """
    return (np.sign(x) * np.ceil( np.floor( np.abs(x) * 2 ) / 2 )).astype(int)

class QuestObject:
    
    """Measure threshold using a Weibull psychometric function.
    
    Threshold 't' is measured on an abstract 'intensity' scale, which
    usually corresponds to log10 contrast.

    The Weibull psychometric function:
    
    p2=delta*gamma+(1-delta)*(1-(1-gamma)*exp(-10**(beta*(x2+xThreshold))))

    where x represents log10 contrast relative to threshold. The
    Weibull function itself appears only in recompute(), which uses
    the specified parameter values in self to compute a psychometric
    function and store it in self. All the other methods simply use
    the psychometric function stored as instance
    variables. recompute() is called solely by __init__() and
    beta_analysis() (and possibly by a few user programs). Thus, if
    you prefer to use a different kind of psychometric function,
    called Foo, you need only subclass QuestObject, overriding
    __init__(), recompute(), and (if you need it) beta_analysis().

    instance variables:
    
    tGuess is your prior threshold estimate.

    tGuessSd is the standard deviation you assign to that guess.

    pThreshold is your threshold criterion expressed as probability of
    response==1. An intensity offset is introduced into the
    psychometric function so that threshold (i.e. the midpoint of the
    table) yields pThreshold.

    beta, delta, and gamma are the parameters of a Weibull
    psychometric function.

    beta controls the steepness of the psychometric
    function. Typically 3.5.

    delta is the fraction of trials on which the observer presses
    blindly.  Typically 0.01.

    gamma is the fraction of trials that will generate response 1 when
    intensity==-inf.

    grain is the quantization of the internal table. E.g. 0.01.

    range is the intensity difference between the largest and smallest
    intensity that the internal table can store. E.g. 5. This interval
    will be centered on the initial guess tGuess,
    i.e. [tGuess-range/2, tGuess+range/2].  QUEST assumes that
    intensities outside of this interval have zero prior probability,
    i.e. they are impossible.

    """
    def __init__(self,tGuess,tGuessSd,pThreshold,beta,delta,gamma,grain=0.01,range=None):
        """Initialize Quest parameters.

        Create an instance of QuestObject with all the information
        necessary to measure threshold.

        This was converted from the Psychtoolbox's QuestCreate function.
        """
        grain = float(grain) # make sure grain is a float
        if range is None:
            dim = 500
        else:
            if range <= 0:
                raise ValueError('argument "range" must be greater than zero.')
            dim=range/grain
            dim=2*math.ceil(dim/2.0) # round up to even integer
        self.updatePdf = True
        self.warnPdf = True
        self.normalizePdf = True # was False but is True in the Psychtoolbox
        self.tGuess = tGuess
        self.tGuessSd = tGuessSd
        self.pThreshold = pThreshold
        self.beta = beta
        self.delta = delta
        self.gamma = gamma
        self.grain = grain
        self.dim = dim
        self.recompute()

    def beta_analysis(self,stream=None):
        """Analyze the quest function with beta as a free parameter.

        It returns the mean estimates of alpha (as logC) and
        beta. Gamma is left at whatever value the user fixed it at.
        """

        def beta_analysis1(stream=None):
            """private function called by beta_analysis()"""
            if stream is None:
                stream=sys.stdout
            q2 = []
            for i in range(1,17):
                q_copy=copy.copy(self)
                q_copy.beta=2**(i/4.0)
                q_copy.dim=250
                q_copy.grain=0.02
                q_copy.recompute() # this is done outside the loop on q2 in Psychtoolbox
                q2.append(q_copy)
            na = np.array # shorthand
            t2    = na([q2i.mean() for q2i in q2])
            p2    = na([q2i.pdf_at(t2i) for q2i,t2i in zip(q2,t2)])
            sd2   = na([q2i.sd() for q2i in q2])
            beta2 = na([q2i.beta for q2i in q2])
            i = np.argmax(p2)
            #i=np.argsort(p2)[-1] # is p,i]=max(p2) in Psychtoolbox
            t=t2[i]
            sd=q2[i].sd()
            p=np.sum(p2)
            betaMean=np.sum(p2*beta2)/p
            betaSd=math.sqrt(np.sum(p2*beta2**2)/p-(np.sum(p2*beta2)/p)**2)
            iBetaMean=np.sum(p2/beta2)/p
            iBetaSd=math.sqrt(np.sum(p2/beta2**2)/p-(np.sum(p2/beta2)/p)**2)
            stream.write('%5.2f	%5.2f	%4.1f	%4.1f	%6.3f\n'%(t,sd,1/iBetaMean,betaSd,self.gamma))
            # where is: return betaEstimate = 1/iBetaMean ???
        print('Now re-analyzing with beta as a free parameter. . . .')
        if stream is None:
            stream=sys.stdout
        stream.write('logC 	 sd 	 beta	 sd	 gamma\n')
        beta_analysis1(stream)

    def mean(self):
        """Mean of Quest posterior pdf.

        Get the mean threshold estimate.

        This was converted from the Psychtoolbox's QuestMean function.
        """
        # there is chunk missing that deals with the case length(q)>1. Implies that never happens here.
        
        return self.tGuess + np.sum(self.pdf*self.x)/np.sum(self.pdf)

    def mode(self):
        """Mode of Quest posterior pdf.
        
        t,p=q.mode()
        't' is the mode threshold estimate
        'p' is the value of the (unnormalized) pdf at t.

        This was converted from the Psychtoolbox's QuestMode function.
        """
        #iMode = np.argsort(self.pdf)[-1]
        iMode = np.argmax(self.pdf)
        p=self.pdf[iMode]
        t=self.x[iMode]+self.tGuess
        return t,p

    def p(self,x):
        """probability of correct response at intensity x.

        p=q.p(x)
        
        The probability of a correct (or yes) response at intensity x,
        assuming threshold is at x=0.
        
        This was converted from the Psychtoolbox's QuestP function.
        """
        if x < self.x2[0]:
            return self.x2[0]
        if x > self.x2[-1]:
            return self.x2[-1]
        return np.interp(x,self.x2,self.p2)
    
    def pdf_at(self,t):
        """The (unnormalized) probability density of candidate threshold 't'.
        
        This was converted from the Psychtoolbox's QuestPdf function.
        """
        i=int(alt_round((t-self.tGuess)/self.grain))+1+self.dim/2 # change for the other round
        i=min(len(self.pdf),max(1,i))-1
        p=self.pdf[i]
        return p

    def quantile(self,quantileOrder=None):
        """Get Quest recommendation for next trial level.

        intensity=q.quantile([quantileOrder])
        
        Gets a quantile of the pdf in the struct q.  You may specify
        the desired quantileOrder, e.g. 0.5 for median, or, making two
        calls, 0.05 and 0.95 for a 90confidence interval.  If the
        'quantileOrder' argument is not supplied, then it's taken from
        the QuestObject instance. __init__() uses recompute() to
        compute the optimal quantileOrder and saves that in the
        QuestObject instance; this quantileOrder yields a quantile
        that is the most informative intensity for the next trial.

        This was converted from the Psychtoolbox's QuestQuantile function.
        """
        if quantileOrder is None:
            quantileOrder = self.quantileOrder
        p = np.cumsum(self.pdf)
        if len(getinf(p[-1])[0]):
            raise RuntimeError('pdf is not finite')
        if p[-1]==0:
            raise RuntimeError('pdf is all zero')
        #m1p = np.concatenate(([-1],p))
        #index = np.nonzero( m1p[1:]-m1p[:-1] )[0]
        index = np.where(np.diff(np.concatenate(([-1], p))) > 0)[0] # more similar to Psychtoolbox than the previous
        if len(index) < 2:
            raise RuntimeError('pdf has only %g nonzero point(s)'%len(index))
        ires = np.interp([quantileOrder*p[-1]],p[index],self.x[index])[0]
        return self.tGuess+ires

    def sd(self):
        """Standard deviation of Quest posterior pdf.

        Get the sd of the threshold distribution.

        This was converted from the Psychtoolbox's QuestSd function."""
        p=np.sum(self.pdf)
        sd=math.sqrt(np.sum(self.pdf*self.x**2)/p-(np.sum(self.pdf*self.x)/p)**2)
        return sd

    def simulate(self,tTest,tActual):
        """Simulate an observer with given Quest parameters.

        response=QuestSimulate(q,intensity,tActual)
        
        Simulate the response of an observer with threshold tActual.

        This was converted from the Psychtoolbox's QuestSimulate function."""
        #t = min( max(tTest-tActual, self.x2[0]), self.x2[-1] )
        x2min = np.min(self.x2[[0, -1]])  # this is equivalent to Psychtoolbox
        x2max = np.max(self.x2[[0, -1]])  # this is equivalent to Psychtoolbox
        t = min(max(tTest-tActual, x2min), x2max) # this is equivalent to Psychtoolbox
        response= np.interp([t],self.x2,self.p2)[0] > random.random()
        return response

    def recompute(self):
        """Recompute the psychometric function & pdf.
        
        Call this immediately after changing a parameter of the
        psychometric function. recompute() uses the specified
        parameters in 'self' to recompute the psychometric
        function. It then uses the newly computed psychometric
        function and the history in self.intensity and self.response
        to recompute the pdf. (recompute() does nothing if q.updatePdf
        is False.)

        This was converted from the Psychtoolbox's QuestRecompute function."""
        if not self.updatePdf:
            return
        if self.gamma > self.pThreshold:
            warnings.warn( 'reducing gamma from %.2f to 0.5'%self.gamma)
            self.gamma = 0.5
        self.i = np.arange(-self.dim/2,self.dim/2+1)
        self.x = self.i * self.grain
        self.pdf = np.exp(-0.5*(self.x/self.tGuessSd)**2)
        self.pdf = self.pdf/np.sum(self.pdf)
        i2 = np.arange(-self.dim,self.dim+1)
        self.x2 = i2*self.grain
        self.p2 = self.delta*self.gamma+(1-self.delta)*(1-(1-self.gamma)*np.exp(-10**(self.beta*self.x2)))
        #if self.p2[0] >= self.pThreshold or self.p2[-1] <= self.pThreshold:
        if self.p2[0] > self.pThreshold or self.p2[-1] < self.pThreshold: # what's in the Psychtoolbox
            raise RuntimeError('psychometric function range [%.2f %.2f] omits %.2f threshold'%(self.p2[0],self.p2[-1],self.pThreshold))
        if len(getinf(self.p2)[0]):
            raise RuntimeError('psychometric function p2 is not finite')
        #index = np.nonzero( self.p2[1:]-self.p2[:-1] )[0] # strictly monotonic subset
        index = np.where(np.diff(self.p2) != 0)[0] # closer to the Psychtoolbox formulation
        if len(index) < 2:
            raise RuntimeError('psychometric function has only %g strictly monotonic points'%len(index))
        self.xThreshold = np.interp([self.pThreshold],self.p2[index],self.x2[index])[0]
        self.p2 = self.delta*self.gamma+(1-self.delta)*(1-(1-self.gamma)*np.exp(-10**(self.beta*(self.x2+self.xThreshold))))
        if len(getinf(self.p2)[0]):
            raise RuntimeError('psychometric function p2 is not finite')
        self.s2 = np.array( ((1-self.p2)[::-1], self.p2[::-1]) )
        if not hasattr(self,'intensity') or not hasattr(self,'response'):
            self.trialCount = 0 # in the Psychtoolbox but not here
            self.intensity = []
            self.response = []
        if len(getinf(self.s2)[0]):
            raise RuntimeError('psychometric function s2 is not finite')

        eps = 2.2204e-16 # as in the Psychtoolbox but was 1e-14

        pL = self.p2[0]
        pH = self.p2[-1]
        pE = pH*math.log(pH+eps)-pL*math.log(pL+eps)+(1-pH+eps)*math.log(1-pH+eps)-(1-pL+eps)*math.log(1-pL+eps)
        pE = 1/(1+math.exp(pE/(pL-pH)))
        self.quantileOrder=(pE-pL)/(pH-pL)
        
        if len(getinf(self.pdf)[0]):
            raise RuntimeError('prior pdf is not finite')

        # recompute the pdf from the historical record of trials
        k=0
        for intensity, response in zip(self.intensity,self.response):
            k+=1
            inten = max(-1e10,min(1e10,intensity)) # make intensity finite
            ii = len(self.pdf) + self.i-alt_round((inten-self.tGuess)/self.grain)-1 # round does not work the same way as in Matlab and the Psychtoolbox; change it
            if ii[0]<0:
                ii = ii-ii[0]
            if ii[-1]>=self.s2.shape[1]:
                ii = ii+self.s2.shape[1]-ii[-1]-1
            iii = ii.astype(np.int_)                       # not in the Psychtoolbox
            if not np.allclose(ii,iii):                    # not in the Psychtoolbox
                raise ValueError('truncation error')        # not in the Psychtoolbox
            self.pdf = self.pdf*self.s2[response,iii]
            if self.normalizePdf and k%100==0:
                self.pdf = self.pdf/np.sum(self.pdf) # avoid underflow; keep the pdf normalized
        if self.normalizePdf:
            self.pdf = self.pdf/np.sum(self.pdf) # avoid underflow; keep the pdf normalized
        if len(getinf(self.pdf)[0]):
            raise RuntimeError('prior pdf is not finite')

    def update(self,intensity,response):
        """Update Quest posterior pdf.

        Update self to reflect the results of this trial. The
        historical records self.intensity and self.response are always
        updated, but self.pdf is only updated if self.updatePdf is
        true. You can always call QuestRecompute to recreate q.pdf
        from scratch from the historical record.

        This was converted from the Psychtoolbox's QuestUpdate function."""
        
        if response < 0 or response > self.s2.shape[0]:
            raise RuntimeError('response %g out of range 0 to %d'%(response,self.s2.shape[0]))
        if self.updatePdf:
            inten = max(-1e10,min(1e10,intensity)) # make intensity finite
            ii = len(self.pdf) + self.i-alt_round((inten-self.tGuess)/self.grain)-1
            #ii = self.pdf.shape[1] + self.i-alt_round((inten-self.tGuess)/self.grain)-1 # change round but otherwise more like Psychtoolbox
            if ii[0]<0 or ii[-1] > self.s2.shape[1]:
                if self.warnPdf:
                    low=(1-len(self.pdf)-self.i[0])*self.grain+self.tGuess # same comment as above
                    high=(self.s2.shape[1]-len(self.pdf)-self.i[-1])*self.grain+self.tGuess # suddenly more like Psychtoolbox
                    warnings.warn( 'intensity %.2f out of range %.2f to %.2f. Pdf will be inexact.'%(intensity,low,high),
                                   RuntimeWarning,stacklevel=2)
                if ii[0]<0:
                    ii = ii-ii[0]
                else:
                    ii = ii+self.s2.shape[1]-ii[-1]-1
            iii = ii.astype(np.int_) # strange
            if not np.allclose(ii,iii):
                raise ValueError('truncation error')
            self.pdf = self.pdf*self.s2[response,iii]
            if self.normalizePdf:
                self.pdf=self.pdf/np.sum(self.pdf)
        # keep a historical record of the trials
        self.intensity.append(intensity)
        self.response.append(response)
        
def demo():
    """Demo script for Quest routines.

    By commenting and uncommenting a few lines in this function, you
    can use this file to implement three QUEST-related procedures for
    measuring threshold.

    QuestMode: In the original algorithm of Watson & Pelli (1983) each
    trial and the final estimate are at the MODE of the posterior pdf.

    QuestMean: In the improved algorithm of King-Smith et al. (1994).
    each trial and the final estimate are at the MEAN of the posterior
    pdf.

    QuestQuantile & QuestMean: In the ideal algorithm of Pelli (1987)
    each trial is at the best QUANTILE, and the final estimate is at
    the MEAN of the posterior pdf.

    This was converted from the Psychtoolbox's QuestDemo function.

    King-Smith, P. E., Grigsby, S. S., Vingrys, A. J., Benes, S. C.,
    and Supowit, A.  (1994) Efficient and unbiased modifications of
    the QUEST threshold method: theory, simulations, experimental
    evaluation and practical implementation.  Vision Res, 34 (7),
    885-912.

    Pelli, D. G. (1987) The ideal psychometric
    procedure. Investigative Ophthalmology & Visual Science, 28
    (Suppl), 366.

    Watson, A. B. and Pelli, D. G. (1983) QUEST: a Bayesian adaptive
    psychometric method. Percept Psychophys, 33 (2), 113-20.
    """
    
    print('The intensity scale is abstract, but usually we think of it as representing log contrast.')

    tActual = 2
    
    tGuess = .9
    
    
    tGuessSd = 2.0 # sd of Gaussian before clipping to specified range
    pThreshold = 0.82
    beta = 3.5
    delta = 0.01
    gamma = 0.5
    q=QuestObject(tGuess,tGuessSd,pThreshold,beta,delta,gamma)
    
    # Simulate a series of trials.
    trialsDesired=1000
    wrongRight = 'wrong', 'right'
    timeZero=time.time()
    for k in range(trialsDesired):
        # Get recommended level.  Choose your favorite algorithm.
        tTest=q.quantile()  # Recommended by Pelli (1987), and still our favorite.
        #tTest=q.mean()     # Recommended by King-Smith et al. (1994)
        #tTest=q.mode()     # Recommended by Watson & Pelli (1983)

        tTest=tTest+random.choice([-0.1,0,0.1])

        # Simulate a trial
        timeSplit=time.time() # omit simulation and printing from reported time/trial.
        response=int(q.simulate(tTest,tActual)/1)

        print('Trial %3d at %4.1f is %s'%(k+1,tTest,wrongRight[int(response)]))
        timeZero=timeZero+time.time()-timeSplit
        
        # Update the pdf
        q.update(tTest,response)

    # Print results of timing.
    print('%.0f ms/trial'%(1000*(time.time()-timeZero)/trialsDesired))

    # Get final estimate.
    t=q.mean() # Recommended by Pelli (1989) and King-Smith et al. (1994). Still our favorite.
    sd=q.sd()
    print('Mean threshold estimate is %4.2f +/- %.2f'%(t,sd))
    #t=QuestMode(q);
    #print 'Mode threshold estimate is %4.2f'%t

    # print('\nQuest beta analysis. Beta controls the steepness of the Weibull function.\n')
    # q.beta_analysis()
    # print('Actual parameters of simulated observer:')
    # print('logC	beta	gamma')
    # print('%5.2f	%4.1f	%5.2f'%(tActual,q.beta,q.gamma))
    
if __name__ == '__main__':
    demo() # run the demo
