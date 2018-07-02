#!/usr/bin/env python
"""ode.py    Ordinary differential equation tools
02-Dec-2007  DA Gutz  Created

"""

def euler(state, rate, irange, dt, lims=None):
    """Simple backward Euler integration on range of list"""
    if lims is not None:
        return [max(min(state[i]+rate[i]*dt, lims[i][1]), lims[i][0])  \
                    for i in irange]
    else:
        return [state[i]+rate[i]*dt \
                    for i in irange]
    
def rk4(obj, dt):
    """Explicit RK4 integration on an object.
    Item                            Description
    obj                             Object that maps past state values to derivatives
    derivs = obj.derivs(pastValues) Method that returns a list of derivatives based
                                    on a list of pastValues
    obj.y                           List of value states
    obj.yp                          List of stored past value states
    obj.ylims                       Corresponding list of state limit tuples,
                                    e.g.  obj.ylims = [(ymin[i], ymax[i]) 
                                    for i in range(len(obj.y))]
    dtime                           Update time
    k1, k2, k3, k4                  Traditional RK4 intermediate derivative
                                    calculations
    return value                    None; rk4 updates the objects state list y

    """
    irange = range(len(obj.y))
    k1 = obj.derivs(obj.yp)
    k2 = obj.derivs(euler(obj.yp, k1, irange, dt/2))
    k3 = obj.derivs(euler(obj.yp, k2, irange, dt/2))
    k4 = obj.derivs(euler(obj.yp, k3, irange, dt))
    rk4Rate = [ (k1[i] + 2*k2[i] + 2*k3[i] + k4[i])/6   for i in irange]
    obj.y = euler(obj.yp, rk4Rate, irange, dt, obj.ylims)
