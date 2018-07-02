#!C:\Python27\python.exe
# Simple time model of GE38 rotor system
# 2-Dec-2007    DA Gutz Created

import cProfile

from pyDAG import LookupTable
from pyDAG import InFile
from pyDAG import ode

class SimpleThreeEngineRotor:
    """Aircraft rotor model
    Dynamic model of GE38 rotor system including:
    - 5-D rotor loading model
    - 11 state rotor dynamics
    The model depends on:
        rotorCurves.txt     Rotor load model (must somehow get in NPSS)
        lookup_table.py     Lookup table method (built into NPSS)
        InFile.py       File input reader (built into NPSS)
        StringSet.py        String handler (built into NPSS)
        ode.py          Ordinary differential equation solver methods (not needed NPSS)
    """
    def __init__(self, dtime):
        "Initialize rotor"
        # Executive setup (not needed in NPSS)
        self.dtime  = dtime     # expected call interval (used by data logging)
        self.time   = 0         # expected time (used by data logging)
        self.count  = 0         # number of calls (used by data logging)

        # GE38 11 state rotor parameters
        self.nomnp  = 14280     # engine power turbine 100% speed, rpm
        self.Jmr    = 0.9065    # lumped main rotor inertia, ft-lb/(rpm/sec)
        self.Jtr    = 0.0599    # lumped tail rotor inertia, ft-lb/(rpm/sec)
        self.Jt     = 0.0481    # lumped transmission rotor inertia, ft-lb/(rpm/sec)
        self.J1     = 0.1160    # lumped engine 1 power turbine inertia, ft-lb/(rpm/sec)
        self.J2     = self.J1   # lumped engine 2 power turbine inertia, ft-lb/(rpm/sec)
        self.J3     = self.J1   # lumped engine 3 power turbine inertia, ft-lb/(rpm/sec)
        self.Kmr    = 27.12     # lumped main rotor shaft spring rate, (ft-lb/sec)/(rpm/sec)
        self.Ktr    = 51.00     # lumped tail rotor shaft spring rate, (ft-lb/sec)/(rpm/sec)
        self.K1     = 852.12    # lumped engine 1 rotor shaft spring rate, (ft-lb/sec)/(rpm/sec)
        self.K2     = 851.32    # lumped engine 2 rotor shaft spring rate, (ft-lb/sec)/(rpm/sec)
        self.K3     = self.K1   # lumped engine 3 rotor shaft spring rate, (ft-lb/sec)/(rpm/sec)
        self.damcoef= 0         # included in load model
        self.datcoef= 2         # NOT included in load model, so must define it here
        self.Dlagm  = 0.826     # main rotor lag-hinge damping, ft-lb/(rpm/sec)
        self.Dht    = 0.165     # Lumped tail rotor shaft damping ft-lbf/(rpm/sec)
        self.Dp1    = 0.0       # engine 1 rotor shaft damping, ft-lb/(rpm/sec)
        self.Dp2    = self.Dp1  # engine 2 rotor shaft damping, ft-lb/(rpm/sec)
        self.Dp3    = self.Dp1  # engine 3 rotor shaft damping, ft-lb/(rpm/sec)
        self.SNmax  = 1.5       # arbitrary fractional max speed limit
        self.SNmin  = 0.01      # arbitrary fractional min speed limit
        # states
        self.Nmr        = self.nomnp    # main rotor speed reflected to engine gear ratio, rpm
        self.Ntr        = self.nomnp    # tail rotor speed reflected to engine gear ratio, rpm
        self.Nt         = self.nomnp    # transmission rotor speed reflected to engine gear ration, rpm
        self.N1         = self.nomnp    # engine 1 power turbine speed, rpm
        self.N2         = self.nomnp    # engine 2 power turbine speed, rpm
        self.N3         = self.nomnp    # engine 3 power turbine speed, rpm
        self.Qmr        = 0             # Main rotor spring preload, ft-lbf
        self.Qtr        = 0             # Tail rotor spring preload, ft-lbf
        self.Q1         = 0             # Engine 1 rotor spring preload, ft-lbf
        self.Q2         = 0             # Engine 2 rotor spring preload, ft-lbf
        self.Q3         = 0             # Engine 3 rotor spring preload, ft-lbf

        # Solver setup
        nx              = self.nomnp*self.SNmax     # Max speed limit
        nn              = self.nomnp*self.SNmin     # Min speed limit
        qx              =  1e5                      # Max torque limit
        qn              = -1e5                      # Min torque limit
        ymax            = [nx,       nx,       nx,      nx,      nx,      nx,      qx,       qx,       qx,      qx,      qx     ]
        self.y          = [self.Nmr, self.Ntr, self.Nt, self.N1, self.N2, self.N3, self.Qmr, self.Qtr, self.Q1, self.Q2, self.Q3]
        ymin            = [nn,       nn,       nn,      nn,      nn,      nn,      qn,       qn,       qn,      qn,      qn     ]
        self.yp         = [x for x in self.y]       # Initialize past value
        self.ylims      = [(ymin[i], ymax[i]) for i in range(len(self.y))]

        # Table call setup (not needed in NPSS)
        self.ALT_T      = []
        self.VKNOT_T    = []
        self.OATF_T     = []
        self.GVW_T      = []
        self.CLP_T      = []
        self.HPTOT_0_0  = LookupTable()
        self.HPTOT_0_1  = LookupTable()
        self.HPTOT_1_0  = LookupTable()
        self.HPTOT_1_1  = LookupTable()
        self.HPTOT_2_0  = LookupTable()
        self.HPTOT_2_1  = LookupTable()
        self.HPMR_0_0   = LookupTable()
        self.HPMR_0_1   = LookupTable()
        self.HPMR_1_0   = LookupTable()
        self.HPMR_1_1   = LookupTable()
        self.HPMR_2_0   = LookupTable()
        self.HPMR_2_1   = LookupTable()
        self.HPTR_0_0   = LookupTable()
        self.HPTR_0_1   = LookupTable()
        self.HPTR_1_0   = LookupTable()
        self.HPTR_1_1   = LookupTable()
        self.HPTR_2_0   = LookupTable()
        self.HPTR_2_1   = LookupTable()

    def assignInputs(self, qmrload, qtrload, qgas1, qgas2, qgas3):
        "Assign the external inputs of the sytem, e.g. the u's of Ax+Bu"
        self.qmrload    = qmrload
        self.qtrload    = qtrload
        self.qgas1      = qgas1
        self.qgas2      = qgas2
        self.qgas3      = qgas3
        self.qtotload   = qmrload + qtrload

    def derivs(self, (Nmr, Ntr, Nt, N1, N2, N3, Qmr, Qtr, Q1, Q2, Q3)):
        "Generalized derivative calculator for the class"
        dNmr    = (-self.qmrload + Qmr  - (Nmr - Nt)*self.Dlagm - self.damcoef*self.qmrload/max(Nmr, 1)*(Nmr-self.nomnp)) / self.Jmr
        self.dNmr = dNmr
        dNtr    = (-self.qtrload + Qtr  - (Ntr - Nt)*self.Dht   - self.datcoef*self.qtrload/max(Ntr, 1)*(Ntr-self.nomnp)) / self.Jtr
        dNt     = ( Q1 + Q2 + Q3 - Qmr - Qtr  \
                   - (Nt - N1 )*self.Dp1 - (Nt - N2)*self.Dp2 - (Nt - N3)*self.Dp3 - (Nt - Nmr)*self.Dlagm - (Nt - Ntr)*self.Dht) / self.Jt
        dN1     = ( self.qgas1  - Q1    - (N1 - Nt )*self.Dp1 ) / self.J1
        dN2     = ( self.qgas2  - Q2    - (N2 - Nt )*self.Dp2 ) / self.J2
        dN3     = ( self.qgas3  - Q3    - (N3 - Nt )*self.Dp3 ) / self.J3
        dQmr    = ( Nt - Nmr )*self.Kmr
        dQtr    = ( Nt - Ntr )*self.Ktr
        dQ1     = ( N1 - Nt ) *self.K1
        dQ2     = ( N2 - Nt ) *self.K2
        dQ3     = ( N3 - Nt ) *self.K3
        return (dNmr, dNtr, dNt, dN1, dN2, dN3, dQmr, dQtr, dQ1, dQ2, dQ3)

    def assignStates(self, N0, qmrload, qtrload, qgas1, qgas2, qgas3):
        "Initialize the state past values"
        self.yp = [N0, N0, N0, N0, N0, N0, qmrload, qtrload, qgas1, qgas2, qgas3]

    def writeCurves(self):
        "Laboriously write the rotor load model"
        curveFile = file('rotorModel.map', 'wb')
        nALT    = len(self.ALT_T)
        nVKNOT  = len(self.VKNOT_T)
        nOATF   = len(self.OATF_T)
        nGVW    = len(self.GVW_T)
        nCLP    = len(self.CLP_T)
        cout = 'Table TB_HPTOT(real alt, real vknots, real oatf, real gvw, real clp) {\n'
        coutm= 'Table TB_HPMR (real alt, real vknots, real oatf, real gvw, real clp) {\n'
        coutt= 'Table TB_HPTR (real alt, real vknots, real oatf, real gvw, real clp) {\n'
        for i in range(nALT):
            cout +='    alt= %(alt)9.1f {\n' %{'alt':self.ALT_T[i]}
            coutm+='    alt= %(alt)9.1f {\n' %{'alt':self.ALT_T[i]}
            coutt+='    alt= %(alt)9.1f {\n' %{'alt':self.ALT_T[i]}
            for j in range(nVKNOT):
                cout +='        vknots= %(vknot)7.1f {\n' %{'vknot':self.VKNOT_T[j]}
                coutm+='        vknots= %(vknot)7.1f {\n' %{'vknot':self.VKNOT_T[j]}
                coutt+='        vknots= %(vknot)7.1f {\n' %{'vknot':self.VKNOT_T[j]}
                for k in range(nOATF):
                    cout +='            oatf= %(oatf)7.2f {\n' %{'oatf':self.OATF_T[k]}
                    coutm+='            oatf= %(oatf)7.2f {\n' %{'oatf':self.OATF_T[k]}
                    coutt+='            oatf= %(oatf)7.2f {\n' %{'oatf':self.OATF_T[k]}
                    for l in range(nGVW):
                        cout +='                gvw= %(gvw)8.1f {\n' %{'gvw':self.GVW_T[l]}
                        cout +='                    clp  = {'
                        coutm+='                gvw= %(gvw)8.1f {\n' %{'gvw':self.GVW_T[l]}
                        coutm+='                    clp  = {'
                        coutt+='                gvw= %(gvw)8.1f {\n' %{'gvw':self.GVW_T[l]}
                        coutt+='                    clp  = {'
                        for m in range(nCLP-1): cout +='%(clp)9.1f,' %{'clp': self.CLP_T[m]}
                        cout +='%(clp)9.1f }\n' %{'clp': self.CLP_T[nCLP-1]}
                        cout +='                    hptot= {'
                        for m in range(nCLP-1): coutm+='%(clp)9.1f,' %{'clp': self.CLP_T[m]}
                        coutm+='%(clp)9.1f }\n' %{'clp': self.CLP_T[nCLP-1]}
                        coutm+='                    hpmr = {'
                        for m in range(nCLP-1): coutt+='%(clp)9.1f,' %{'clp': self.CLP_T[m]}
                        coutt+='%(clp)9.1f }\n' %{'clp': self.CLP_T[nCLP-1]}
                        coutt+='                    hptr = {'
                        for m in range(nCLP-1):
                            index = m + (l + (k + (j + i*nVKNOT)*nOATF)*nGVW)*nCLP;
                            cout +='%(hptot)9.1f,' %{'hptot': self.HPTOT[index]}
                            coutm+='%(hpmr)9.1f,' %{'hpmr': self.HPMR[index]}
                            coutt+='%(hptr)9.1f,' %{'hptr': self.HPTR[index]}
                        index = (nCLP-1) + (l + (k + (j + i*nVKNOT)*nOATF)*nGVW)*nCLP;
                        cout +='%(hptot)9.1f }\n' %{'hptot': self.HPTOT[index]}
                        cout +='                }\n'
                        coutm+='%(hpmr)9.1f }\n' %{'hpmr': self.HPMR[index]}
                        coutm+='                }\n'
                        coutt+='%(hptr)9.1f }\n' %{'hptr': self.HPTR[index]}
                        coutt+='                }\n'
                    cout +='            }\n'
                    coutm+='            }\n'
                    coutt+='            }\n'
                cout +='        }\n'
                coutm+='        }\n'
                coutt+='        }\n'
            cout +='    }\n'
            coutm+='    }\n'
            coutt+='    }\n'
        cout +='}\n'
        coutm+='}\n'
        coutt+='}\n'
        curveFile.write(cout)
        curveFile.write(coutm)
        curveFile.write(coutt)

    def loadCurves(self):
        "Laboriously import the rotor load model"
        curves  = InFile('rotorCurves.txt')
        curves.load()
        curves.tokenize(' \n')
        if not (curves.token(0,0)=='ALT'     and \
                curves.token(0,1)=='VKNOT'   and \
                curves.token(0,2)=='OATF'    and \
                curves.token(0,3)=='GVW'     and \
                curves.token(0,4)=='CLP'     and \
                curves.token(0,5)=='HPTOT_T' and \
                curves.token(0,6)=='HPMR_T'  and \
                curves.token(0,7)=='HPTR_T'):
            print curves.Line(0)
            print 'token0=', curves.token(0,0)
            print 'token1=', curves.token(0,1)
            print 'token2=', curves.token(0,2)
            print 'token3=', curves.token(0,3)
            print 'token4=', curves.token(0,4)
            print 'token5=', curves.token(0,5)
            print 'token6=', curves.token(0,6)
            print 'token7=', curves.token(0,7)
            print 'Error(loadCurves): bad header'
            return -1
        nL      = curves.numLines
        nALT    = 0
        for i in range(1, nL):
            alt = float(curves.token(i, 1))
            if nALT==0 or alt>self.ALT_T[nALT-1]:
                self.ALT_T += [alt]
                nALT += 1
            elif alt<self.ALT_T[nALT-1]:
                break
        nVKNOT  = 0
        for j in range(1, nL):
            vknot = float(curves.token(j, 2))
            if nVKNOT==0 or vknot>self.VKNOT_T[nVKNOT-1]:
                self.VKNOT_T += [vknot]
                nVKNOT += 1
            elif vknot<self.VKNOT_T[nVKNOT-1]:
                break
        nOATF   = 0
        for k in range(1, nL):
            oatf = float(curves.token(k, 3))
            if nOATF==0 or oatf>self.OATF_T[nOATF-1]:
                self.OATF_T += [oatf]
                nOATF += 1
            elif oatf<self.OATF_T[nOATF-1]:
                break
        nGVW    = 0
        for l in range(1, nL):
            gvw = float(curves.token(l, 4))
            if nGVW==0 or gvw>self.GVW_T[nGVW-1]:
                self.GVW_T += [gvw]
                nGVW += 1
            elif gvw<self.GVW_T[nGVW-1]:
                break
        nCLP    = 0
        for m in range(1, nL):
            clp = float(curves.token(m, 5))
            if nCLP==0 or clp>self.CLP_T[nCLP-1]:
                self.CLP_T += [clp]
                nCLP += 1
            elif clp<self.CLP_T[nCLP-1]:
                break
        HPTOT   = []
        HPMR    = []
        HPTR    = []
        for i in range(1, nL):
            HPTOT += [float(curves.token(i, 6))]
            HPMR  += [float(curves.token(i, 7))]
            #HPTR  += [float(curves.token(i, 6)) - float(curves.token(i, 7)) ]
            HPTR  += [float(curves.token(i, 8))]
        if False:
            print 'ALT_T=',     self.ALT_T
            print 'VKNOT_T=',   self.VKNOT_T
            print 'OATF_T=',    self.OATF_T
            print 'GVW_T=',     self.GVW_T
            print 'CLP_T=',     self.CLP_T
            print 'nL=',        nL
            print 'nALT=', nALT, 'nVKNOT=', nVKNOT, 'nOATF=', nOATF, 'nGVW=', nGVW, 'nCLP=', nCLP
        HPTOT_T = []
        HPMR_T  = []
        HPTR_T  = []
        for i in range(nALT):
            HPTOTj  = []
            HPMRj   = []
            HPTRj   = []
            for j in range(nVKNOT):
                HPTOTk  = []
                HPMRk   = []
                HPTRk   = []
                for k in range(nOATF):
                    HPTOTl  = []
                    HPMRl   = []
                    HPTRl   = []
                    for l in range(nGVW):
                        HPTOTm  = []
                        HPMRm   = []
                        HPTRm   = []
                        for m in range(nCLP):
                            index = m + (l + (k + (j + i*nVKNOT)*nOATF)*nGVW)*nCLP;
                            HPTOTm += [HPTOT[index]]
                            HPMRm  += [HPMR[index]]
                            HPTRm  += [HPTR[index]]
                        HPTOTl  += [HPTOTm]
                        HPMRl   += [HPMRm]
                        HPTRl   += [HPTRm]
                    HPTOTk  += [HPTOTl]
                    HPMRk   += [HPMRl]
                    HPTRk   += [HPTRl]
                HPTOTj  += [HPTOTk]
                HPMRj   += [HPMRk]
                HPTRj   += [HPTRk]
            HPTOT_T     += [HPTOTj]
            HPMR_T      += [HPMRj]
            HPTR_T      += [HPTRj]
        self.HPTOT_0_0.addAxis('x', self.OATF_T)
        self.HPTOT_0_0.addAxis('y', self.GVW_T)
        self.HPTOT_0_0.addAxis('z', self.CLP_T)
        self.HPTOT_0_0.setValueTable(HPTOT_T[0][0])
        self.HPTOT_0_1.addAxis('x', self.OATF_T)
        self.HPTOT_0_1.addAxis('y', self.GVW_T)
        self.HPTOT_0_1.addAxis('z', self.CLP_T)
        self.HPTOT_0_1.setValueTable(HPTOT_T[0][1])
        self.HPTOT_1_0.addAxis('x', self.OATF_T)
        self.HPTOT_1_0.addAxis('y', self.GVW_T)
        self.HPTOT_1_0.addAxis('z', self.CLP_T)
        self.HPTOT_1_0.setValueTable(HPTOT_T[1][0])
        self.HPTOT_1_1.addAxis('x', self.OATF_T)
        self.HPTOT_1_1.addAxis('y', self.GVW_T)
        self.HPTOT_1_1.addAxis('z', self.CLP_T)
        self.HPTOT_1_1.setValueTable(HPTOT_T[1][1])
        self.HPTOT_2_0.addAxis('x', self.OATF_T)
        self.HPTOT_2_0.addAxis('y', self.GVW_T)
        self.HPTOT_2_0.addAxis('z', self.CLP_T)
        self.HPTOT_2_0.setValueTable(HPTOT_T[2][0])
        self.HPTOT_2_1.addAxis('x', self.OATF_T)
        self.HPTOT_2_1.addAxis('y', self.GVW_T)
        self.HPTOT_2_1.addAxis('z', self.CLP_T)
        self.HPTOT_2_1.setValueTable(HPTOT_T[2][1])
        self.HPMR_0_0.addAxis('x', self.OATF_T)
        self.HPMR_0_0.addAxis('y', self.GVW_T)
        self.HPMR_0_0.addAxis('z', self.CLP_T)
        self.HPMR_0_0.setValueTable(HPMR_T[0][0])
        self.HPMR_0_1.addAxis('x', self.OATF_T)
        self.HPMR_0_1.addAxis('y', self.GVW_T)
        self.HPMR_0_1.addAxis('z', self.CLP_T)
        self.HPMR_0_1.setValueTable(HPMR_T[0][1])
        self.HPMR_1_0.addAxis('x', self.OATF_T)
        self.HPMR_1_0.addAxis('y', self.GVW_T)
        self.HPMR_1_0.addAxis('z', self.CLP_T)
        self.HPMR_1_0.setValueTable(HPMR_T[1][0])
        self.HPMR_1_1.addAxis('x', self.OATF_T)
        self.HPMR_1_1.addAxis('y', self.GVW_T)
        self.HPMR_1_1.addAxis('z', self.CLP_T)
        self.HPMR_1_1.setValueTable(HPMR_T[1][1])
        self.HPMR_2_0.addAxis('x', self.OATF_T)
        self.HPMR_2_0.addAxis('y', self.GVW_T)
        self.HPMR_2_0.addAxis('z', self.CLP_T)
        self.HPMR_2_0.setValueTable(HPMR_T[2][0])
        self.HPMR_2_1.addAxis('x', self.OATF_T)
        self.HPMR_2_1.addAxis('y', self.GVW_T)
        self.HPMR_2_1.addAxis('z', self.CLP_T)
        self.HPMR_2_1.setValueTable(HPMR_T[2][1])
        self.HPTR_0_0.addAxis('x', self.OATF_T)
        self.HPTR_0_0.addAxis('y', self.GVW_T)
        self.HPTR_0_0.addAxis('z', self.CLP_T)
        self.HPTR_0_0.setValueTable(HPTR_T[0][0])
        self.HPTR_0_1.addAxis('x', self.OATF_T)
        self.HPTR_0_1.addAxis('y', self.GVW_T)
        self.HPTR_0_1.addAxis('z', self.CLP_T)
        self.HPTR_0_1.setValueTable(HPTR_T[0][1])
        self.HPTR_1_0.addAxis('x', self.OATF_T)
        self.HPTR_1_0.addAxis('y', self.GVW_T)
        self.HPTR_1_0.addAxis('z', self.CLP_T)
        self.HPTR_1_0.setValueTable(HPTR_T[1][0])
        self.HPTR_1_1.addAxis('x', self.OATF_T)
        self.HPTR_1_1.addAxis('y', self.GVW_T)
        self.HPTR_1_1.addAxis('z', self.CLP_T)
        self.HPTR_1_1.setValueTable(HPTR_T[1][1])
        self.HPTR_2_0.addAxis('x', self.OATF_T)
        self.HPTR_2_0.addAxis('y', self.GVW_T)
        self.HPTR_2_0.addAxis('z', self.CLP_T)
        self.HPTR_2_0.setValueTable(HPTR_T[2][0])
        self.HPTR_2_1.addAxis('x', self.OATF_T)
        self.HPTR_2_1.addAxis('y', self.GVW_T)
        self.HPTR_2_1.addAxis('z', self.CLP_T)
        self.HPTR_2_1.setValueTable(HPTR_T[2][1])
        self.HPTOT  = HPTOT
        self.HPMR   = HPMR
        self.HPTR   = HPTR

    def loadLookup(self, alt, vknot, oatf, gvw, dynang):
        "Perform 5-D table lookup for rotor loads (extrapolates)"
        self.alt            = alt
        self.vknot          = vknot
        self.oatf           = oatf
        self.gvw            = gvw
        self.DYNANG         = dynang
        hptot_0kts_0ft      = self.HPTOT_0_0.lookup(x=oatf, y=gvw, z=dynang)
        hptot_0kts_3kft     = self.HPTOT_0_1.lookup(x=oatf, y=gvw, z=dynang)
        hptot_80kts_0ft     = self.HPTOT_1_0.lookup(x=oatf, y=gvw, z=dynang)
        hptot_80kts_3kft    = self.HPTOT_1_1.lookup(x=oatf, y=gvw, z=dynang)
        hptot_160kts_0ft    = self.HPTOT_2_0.lookup(x=oatf, y=gvw, z=dynang)
        hptot_160kts_3kft   = self.HPTOT_2_1.lookup(x=oatf, y=gvw, z=dynang)

        hpmr_0kts_0ft       = self.HPMR_0_0.lookup(x=oatf, y=gvw, z=dynang)
        hpmr_0kts_3kft      = self.HPMR_0_1.lookup(x=oatf, y=gvw, z=dynang)
        hpmr_80kts_0ft      = self.HPMR_1_0.lookup(x=oatf, y=gvw, z=dynang)
        hpmr_80kts_3kft     = self.HPMR_1_1.lookup(x=oatf, y=gvw, z=dynang)
        hpmr_160kts_0ft     = self.HPMR_2_0.lookup(x=oatf, y=gvw, z=dynang)
        hpmr_160kts_3kft    = self.HPMR_2_1.lookup(x=oatf, y=gvw, z=dynang)

        hptr_0kts_0ft       = self.HPTR_0_0.lookup(x=oatf, y=gvw, z=dynang)
        hptr_0kts_3kft      = self.HPTR_0_1.lookup(x=oatf, y=gvw, z=dynang)
        hptr_80kts_0ft      = self.HPTR_1_0.lookup(x=oatf, y=gvw, z=dynang)
        hptr_80kts_3kft     = self.HPTR_1_1.lookup(x=oatf, y=gvw, z=dynang)
        hptr_160kts_0ft     = self.HPTR_2_0.lookup(x=oatf, y=gvw, z=dynang)
        hptr_160kts_3kft    = self.HPTR_2_1.lookup(x=oatf, y=gvw, z=dynang)


        if vknot<self.VKNOT_T[1]:
            hptotv0 = ( vknot - self.VKNOT_T[0] ) / ( self.VKNOT_T[1] - self.VKNOT_T[0] ) * ( hptot_80kts_0ft  - hptot_0kts_0ft  ) + hptot_0kts_0ft
            hptotv1 = ( vknot - self.VKNOT_T[0] ) / ( self.VKNOT_T[1] - self.VKNOT_T[0] ) * ( hptot_80kts_3kft - hptot_0kts_3kft ) + hptot_0kts_3kft
            hpmrv0  = ( vknot - self.VKNOT_T[0] ) / ( self.VKNOT_T[1] - self.VKNOT_T[0] ) * ( hpmr_80kts_0ft   - hpmr_0kts_0ft   ) + hpmr_0kts_0ft
            hpmrv1  = ( vknot - self.VKNOT_T[0] ) / ( self.VKNOT_T[1] - self.VKNOT_T[0] ) * ( hpmr_80kts_3kft  - hpmr_0kts_3kft  ) + hpmr_0kts_3kft
            hptrv0  = ( vknot - self.VKNOT_T[0] ) / ( self.VKNOT_T[1] - self.VKNOT_T[0] ) * ( hptr_80kts_0ft   - hptr_0kts_0ft   ) + hptr_0kts_0ft
            hptrv1  = ( vknot - self.VKNOT_T[0] ) / ( self.VKNOT_T[1] - self.VKNOT_T[0] ) * ( hptr_80kts_3kft  - hptr_0kts_3kft  ) + hptr_0kts_3kft
        else:
            hptotv0 = ( vknot - self.VKNOT_T[1] ) / ( self.VKNOT_T[2] - self.VKNOT_T[1] ) * ( hptot_160kts_0ft  - hptot_80kts_0ft  ) + hptot_80kts_0ft
            hptotv1 = ( vknot - self.VKNOT_T[1] ) / ( self.VKNOT_T[2] - self.VKNOT_T[1] ) * ( hptot_160kts_3kft - hptot_80kts_3kft ) + hptot_80kts_3kft
            hpmrv0  = ( vknot - self.VKNOT_T[1] ) / ( self.VKNOT_T[2] - self.VKNOT_T[1] ) * ( hpmr_160kts_0ft   - hpmr_80kts_0ft   ) + hpmr_80kts_0ft
            hpmrv1  = ( vknot - self.VKNOT_T[1] ) / ( self.VKNOT_T[2] - self.VKNOT_T[1] ) * ( hpmr_160kts_3kft  - hpmr_80kts_3kft  ) + hpmr_80kts_3kft
            hptrv0  = ( vknot - self.VKNOT_T[1] ) / ( self.VKNOT_T[2] - self.VKNOT_T[1] ) * ( hptr_160kts_0ft   - hptr_80kts_0ft   ) + hptr_80kts_0ft
            hptrv1  = ( vknot - self.VKNOT_T[1] ) / ( self.VKNOT_T[2] - self.VKNOT_T[1] ) * ( hptr_160kts_3kft  - hptr_80kts_3kft  ) + hptr_80kts_3kft
        self.hptot  = ( alt   - self.ALT_T[0]   ) / ( self.ALT_T[1]   - self.ALT_T[0]   ) * ( hptotv1 - hptotv0 ) + hptotv0
        self.hpmr   = ( alt   - self.ALT_T[0]   ) / ( self.ALT_T[1]   - self.ALT_T[0]   ) * ( hpmrv1  - hpmrv0  ) + hpmrv0
        self.hptr   = ( alt   - self.ALT_T[0]   ) / ( self.ALT_T[1]   - self.ALT_T[0]   ) * ( hptrv1  - hptrv0  ) + hptrv0
        self.qtotload   = self.hptot / self.Nmr * 5252.1131
        self.qmrload    = self.hpmr  / self.Nmr * 5252.1131
        self.qtrload    = self.hptr  / self.Ntr * 5252.1131
        return self.qtotload, self.qmrload, self.qtrload

    def update(self):
        self.Nmr    = self.y[0]
        self.Ntr    = self.y[1]
        self.Nt     = self.y[2]
        self.N1     = self.y[3]
        self.N2     = self.y[4]
        self.N3     = self.y[5]
        self.Qmr    = self.y[6]
        self.Qtr    = self.y[7]
        self.Q1     = self.y[8]
        self.Q2     = self.y[9]
        self.Q3     = self.y[10]
        self.count +=1
        self.time   = self.count*self.dtime
        self.yp = [x for x in self.y]

    def __repr__(self):
        "Print result"
        if 1==self.count:
            cout = 'time, alt, vknot, gvw, DYNANG, Nmr, Ntr, Nt, N1, N2, N3, Qmr, Qtr, Q1, Q2, Q3, qgas1, qgas2, qgas3, qtotload, qmrload, qtrload\n'
        else:
            cout = ''
        if self.count%1==0 or self.count==1:
            cout += '%(time)g, %(alt)g, %(vknot)g, %(gvw)g, %(DYNANG)g, %(Nmr)g, %(Ntr)g, %(Nt)g, %(N1)g, %(N2)g, %(N3)g, %(Qmr)g, %(Qtr)g, %(Q1)g, %(Q2)g, %(Q3)g, %(qgas1)g, %(qgas2)g, %(qgas3)g, %(qtotload)g, %(qmrload)g, %(qtrload)g,\n' \
            %{'time':self.time-self.dtime,  'alt':self.alt,         'vknot':self.vknot, 'gvw':self.gvw,     'DYNANG':self.DYNANG,   'Nmr':self.Nmr,     'Ntr':self.Ntr,     'Nt':self.Nt,   'N1':self.N1,   'N2':self.N2,   'N3':self.N3, \
              'Qmr':self.Qmr,       'Qtr':self.Qtr,         'Q1':self.Q1,       'Q2':self.Q2,       'Q3':self.Q3,   \
              'qgas1':self.qgas1,   'qgas2':self.qgas2,     'qgas3':self.qgas3, 'qtotload':self.qtotload,   'qmrload':self.qmrload, 'qtrload':self.qtrload, \
              }
        return cout

# Testing
import sys
def main(args):
    import rotorModel
    # Initial inputs
    dQload      = 0
    ZDYNANG     = 70
    alt         = 3000
    vknot       = 0.01
    oatf        = 59
    gvw         = 46000
    finalTime   = 30
    dtime       = 0.006

    # Setup the rotor model
    R = rotorModel.SimpleThreeEngineRotor(dtime)

    if R.loadCurves() == -1:
        print 'failed to load rotorCurves'
        return -1

    R.writeCurves()

    # Executive intialization
    NOMNP = R.nomnp
    i = 0
    resultsFile = file('rotorModel.csv', 'wb')

    resultsFile = file('rotorModel.csv', 'wb')

    # Rotor initialization
    (qtotload, qmrload, qtrload) = R.loadLookup(alt, vknot, oatf, gvw, ZDYNANG)
    qgas1   = qtotload/3
    qgas2   = qtotload/3
    qgas3   = qtotload/3
    R.assignStates(NOMNP, qmrload, qtrload, qgas1, qgas2, qgas3)
    print 'time=', 0, 'alt=', alt, 'vknot=', vknot, 'oatf=', oatf, 'gvw=', gvw, 'clp=', ZDYNANG

    # Main time loop
    while True:
        time = i*dtime

        # Collective input
        if   time>5 and time < 8:
            dDYNANG =  10
        elif time>8 and time <11:
            dDYNANG = -10
        else:
            dDYNANG = 0
        #dDYNANG=0
        dynang = ZDYNANG+dDYNANG

        # Lookup load model
        (qtotload, qmrload, qtrload) = R.loadLookup(alt, vknot, oatf, gvw, dynang)

        # Assign inputs to rotor object
        R.assignInputs(qmrload, qtrload, qgas1, qgas2, qgas3)

        # Integrate and update the rotor object
        ode.rk4(R, dtime)
        R.update()

        # Write results
        pcnr    = R.Nmr/NOMNP*100
        resultsFile.write(R.__repr__())
        if finalTime<=time: break
        i += 1

    print 'time=', time, 'vknot=', vknot, 'alt=', alt, 'pcnr=', pcnr, 'gvw=', gvw, 'clp=', ZDYNANG

if __name__=='__main__':
    sys.exit(main(sys.argv[1:]))
    #sys.exit(cProfile.run("main(sys.argv[1:])"))
