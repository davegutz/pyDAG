#!/bin/python
"""
Simple time model of GE38 rotor system
2-Dec-2007    DA Gutz Created
python rotorModel.py
>>> main()
alt_t= [0.0, 5000.0, 10000.0, 15000.0, 20000.0]
vknot_t= [0.0, 85.0, 170.0]
oatf_t= [-60.0, -30.0, 0.0, 30.0, 60.0, 90.0, 120.0]
gvw_t= [46000.0, 65500.0, 85000.0]
clp_t= [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
n_l= 3466
d_alt= 5 n_vknot= 3 n_oatf= 7 n_gvw= 3 n_clp= 11
time= 30.0 vknot= 0.01 alt= 3000 pcnr= 100.0 gvw= 46000 clp= 70
"""
# import cProfile
import sys
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

    def __init__(self, d_time):
        """Initialize rotor"""
        # Executive setup (not needed in NPSS)
        self.d_time = d_time  # expected call interval (used by data logging)
        self.time = 0  # expected time (used by data logging)
        self.count = 0  # number of calls (used by data logging)

        # GE38 11 state rotor parameters
        self.nomnp = 14280  # engine power turbine 100% speed, rpm
        self.jmr = 0.9065  # lumped main rotor inertia, ft-lb/(rpm/sec)
        self.jtr = 0.0599  # lumped tail rotor inertia, ft-lb/(rpm/sec)
        self.jt = 0.0481  # lumped transmission rotor inertia, ft-lb/(rpm/sec)
        self.j1 = 0.1160  # lumped engine 1 power turbine inertia, ft-lb/(rpm/sec)
        self.j2 = self.j1  # lumped engine 2 power turbine inertia, ft-lb/(rpm/sec)
        self.j3 = self.j1  # lumped engine 3 power turbine inertia, ft-lb/(rpm/sec)
        self.Kmr = 27.12  # lumped main rotor shaft spring rate, (ft-lb/sec)/(rpm/sec)
        self.Ktr = 51.00  # lumped tail rotor shaft spring rate, (ft-lb/sec)/(rpm/sec)
        self.K1 = 852.12  # lumped engine 1 rotor shaft spring rate, (ft-lb/sec)/(rpm/sec)
        self.K2 = 851.32  # lumped engine 2 rotor shaft spring rate, (ft-lb/sec)/(rpm/sec)
        self.K3 = self.K1  # lumped engine 3 rotor shaft spring rate, (ft-lb/sec)/(rpm/sec)
        self.damcoef = 0  # included in load model
        self.datcoef = 2  # NOT included in load model, so must define it here
        self.dlagm = 0.826  # main rotor lag-hinge damping, ft-lb/(rpm/sec)
        self.Dht = 0.165  # Lumped tail rotor shaft damping ft-lbf/(rpm/sec)
        self.dp1 = 0.0  # engine 1 rotor shaft damping, ft-lb/(rpm/sec)
        self.dp2 = self.dp1  # engine 2 rotor shaft damping, ft-lb/(rpm/sec)
        self.dp3 = self.dp1  # engine 3 rotor shaft damping, ft-lb/(rpm/sec)
        self.sn_max = 1.5  # arbitrary fractional max speed limit
        self.sn_min = 0.01  # arbitrary fractional min speed limit
        # states
        self.n_mr = self.nomnp  # main rotor speed reflected to engine gear ratio, rpm
        self.n_tr = self.nomnp  # tail rotor speed reflected to engine gear ratio, rpm
        self.nt = self.nomnp    # transmission rotor speed reflected to engine gear ration, rpm
        self.n1 = self.nomnp  # engine 1 power turbine speed, rpm
        self.n2 = self.nomnp  # engine 2 power turbine speed, rpm
        self.n3 = self.nomnp  # engine 3 power turbine speed, rpm
        self.qmr = 0  # Main rotor spring preload, ft-lbf
        self.qtr = 0  # Tail rotor spring preload, ft-lbf
        self.q1 = 0  # Engine 1 rotor spring preload, ft-lbf
        self.q2 = 0  # Engine 2 rotor spring preload, ft-lbf
        self.q3 = 0  # Engine 3 rotor spring preload, ft-lbf

        # Solver setup
        nx = self.nomnp * self.sn_max  # Max speed limit
        nn = self.nomnp * self.sn_min  # Min speed limit
        qx = 1e5  # Max torque limit
        qn = -1e5  # Min torque limit
        y_max = [nx, nx, nx, nx, nx, nx, qx, qx, qx, qx, qx]
        self.y = [self.n_mr, self.n_tr, self.nt, self.n1, self.n2, self.n3, self.qmr, self.qtr, self.q1, self.q2,
                  self.q3]
        y_min = [nn, nn, nn, nn, nn, nn, qn, qn, qn, qn, qn]
        self.yp = [x for x in self.y]  # Initialize past value
        self.ylims = [(y_min[i], y_max[i]) for i in range(len(self.y))]

        # Table call setup (not needed in NPSS)
        self.alt_t = []
        self.vknot_t = []
        self.oatf_t = []
        self.gvw_t = []
        self.clp_t = []
        self.hptot_0_0 = LookupTable()
        self.hptot_0_1 = LookupTable()
        self.hptot_1_0 = LookupTable()
        self.hptot_1_1 = LookupTable()
        self.hptot_2_0 = LookupTable()
        self.hptot_2_1 = LookupTable()
        self.hpmr_0_0 = LookupTable()
        self.hpmr_0_1 = LookupTable()
        self.hpmr_1_0 = LookupTable()
        self.hpmr_1_1 = LookupTable()
        self.hpmr_2_0 = LookupTable()
        self.hpmr_2_1 = LookupTable()
        self.hptr_0_0 = LookupTable()
        self.hptr_0_1 = LookupTable()
        self.hptr_1_0 = LookupTable()
        self.hptr_1_1 = LookupTable()
        self.hptr_2_0 = LookupTable()
        self.hptr_2_1 = LookupTable()

    def assign_inputs(self, qmrload, qtrload, qgas1, qgas2, qgas3):
        """Assign the external inputs of the system, e.g. the u's of Ax+Bu"""
        self.qmrload = qmrload
        self.qtrload = qtrload
        self.qgas1 = qgas1
        self.qgas2 = qgas2
        self.qgas3 = qgas3
        self.qtotload = qmrload + qtrload

    def derivs(self, (n_mr, n_tr, nt, n1, n2, n3, qmr, qtr, q1, q2, q3)):
        """Generalized derivative calculator for the class"""
        d_nmr = (-self.qmrload + qmr - (n_mr - nt) * self.dlagm - self.damcoef * self.qmrload / max(n_mr, 1) * (
                    n_mr - self.nomnp)) / self.jmr
        self.d_nmr = d_nmr
        d_ntr = (-self.qtrload + qtr - (n_tr - nt) * self.Dht - self.datcoef * self.qtrload / max(n_tr, 1) * (
                    n_tr - self.nomnp)) / self.jtr
        d_nt = (q1 + q2 + q3 - qmr - qtr
                - (nt - n1) * self.dp1 - (nt - n2) * self.dp2 - (nt - n3) * self.dp3 - (nt - n_mr) * self.dlagm - (
                           nt - n_tr) * self.Dht) / self.jt
        dn1 = (self.qgas1 - q1 - (n1 - nt) * self.dp1) / self.j1
        dn2 = (self.qgas2 - q2 - (n2 - nt) * self.dp2) / self.j2
        dn3 = (self.qgas3 - q3 - (n3 - nt) * self.dp3) / self.j3
        d_qmr = (nt - n_mr) * self.Kmr
        d_qtr = (nt - n_tr) * self.Ktr
        d_q1 = (n1 - nt) * self.K1
        d_q2 = (n2 - nt) * self.K2
        d_q3 = (n3 - nt) * self.K3
        return d_nmr, d_ntr, d_nt, dn1, dn2, dn3, d_qmr, d_qtr, d_q1, d_q2, d_q3

    def assign_states(self, n0, qmrload, qtrload, qgas1, qgas2, qgas3):
        """Initialize the state past values"""
        self.yp = [n0, n0, n0, n0, n0, n0, qmrload, qtrload, qgas1, qgas2, qgas3]

    def write_curves(self):
        """Laboriously write the rotor load model"""
        curve_file = file('rotorModel.map', 'wb')
        d_alt = len(self.alt_t)
        n_vknot = len(self.vknot_t)
        n_oatf = len(self.oatf_t)
        n_gvw = len(self.gvw_t)
        n_clp = len(self.clp_t)
        cout = 'Table TB_hptot(real alt, real vknots, real oatf, real gvw, real clp) {\n'
        coutm = 'Table TB_hpmr (real alt, real vknots, real oatf, real gvw, real clp) {\n'
        coutt = 'Table TB_hptr (real alt, real vknots, real oatf, real gvw, real clp) {\n'
        for i in range(d_alt):
            cout += '    alt= %(alt)9.1f {\n' % {'alt': self.alt_t[i]}
            coutm += '    alt= %(alt)9.1f {\n' % {'alt': self.alt_t[i]}
            coutt += '    alt= %(alt)9.1f {\n' % {'alt': self.alt_t[i]}
            for j in range(n_vknot):
                cout += '        vknots= %(vknot)7.1f {\n' % {'vknot': self.vknot_t[j]}
                coutm += '        vknots= %(vknot)7.1f {\n' % {'vknot': self.vknot_t[j]}
                coutt += '        vknots= %(vknot)7.1f {\n' % {'vknot': self.vknot_t[j]}
                for k in range(n_oatf):
                    cout += '            oatf= %(oatf)7.2f {\n' % {'oatf': self.oatf_t[k]}
                    coutm += '            oatf= %(oatf)7.2f {\n' % {'oatf': self.oatf_t[k]}
                    coutt += '            oatf= %(oatf)7.2f {\n' % {'oatf': self.oatf_t[k]}
                    for l in range(n_gvw):
                        cout += '                gvw= %(gvw)8.1f {\n' % {'gvw': self.gvw_t[l]}
                        cout += '                    clp  = {'
                        coutm += '                gvw= %(gvw)8.1f {\n' % {'gvw': self.gvw_t[l]}
                        coutm += '                    clp  = {'
                        coutt += '                gvw= %(gvw)8.1f {\n' % {'gvw': self.gvw_t[l]}
                        coutt += '                    clp  = {'
                        for m in range(n_clp - 1):
                            cout += '%(clp)9.1f,' % {'clp': self.clp_t[m]}
                        cout += '%(clp)9.1f }\n' % {'clp': self.clp_t[n_clp - 1]}
                        cout += '                    hptot= {'
                        for m in range(n_clp - 1):
                            coutm += '%(clp)9.1f,' % {'clp': self.clp_t[m]}
                        coutm += '%(clp)9.1f }\n' % {'clp': self.clp_t[n_clp - 1]}
                        coutm += '                    hpmr = {'
                        for m in range(n_clp - 1):
                            coutt += '%(clp)9.1f,' % {'clp': self.clp_t[m]}
                        coutt += '%(clp)9.1f }\n' % {'clp': self.clp_t[n_clp - 1]}
                        coutt += '                    hptr = {'
                        for m in range(n_clp - 1):
                            index = m + (l + (k + (j + i * n_vknot) * n_oatf) * n_gvw) * n_clp
                            cout += '%(hptot)9.1f,' % {'hptot': self.hptot[index]}
                            coutm += '%(hpmr)9.1f,' % {'hpmr': self.hpmr[index]}
                            coutt += '%(hptr)9.1f,' % {'hptr': self.hptr[index]}
                        index = (n_clp - 1) + (l + (k + (j + i * n_vknot) * n_oatf) * n_gvw) * n_clp
                        cout += '%(hptot)9.1f }\n' % {'hptot': self.hptot[index]}
                        cout += '                }\n'
                        coutm += '%(hpmr)9.1f }\n' % {'hpmr': self.hpmr[index]}
                        coutm += '                }\n'
                        coutt += '%(hptr)9.1f }\n' % {'hptr': self.hptr[index]}
                        coutt += '                }\n'
                    cout += '            }\n'
                    coutm += '            }\n'
                    coutt += '            }\n'
                cout += '        }\n'
                coutm += '        }\n'
                coutt += '        }\n'
            cout += '    }\n'
            coutm += '    }\n'
            coutt += '    }\n'
        cout += '}\n'
        coutm += '}\n'
        coutt += '}\n'
        curve_file.write(cout)
        curve_file.write(coutm)
        curve_file.write(coutt)

    def load_curves(self):
        """Laboriously import the rotor load model"""
        curves = InFile('rotorCurves.txt')
        curves.load()
        curves.tokenize(' \n\r')
        if not (curves.token(0, 1) == 'ALT' and
                curves.token(0, 2) == 'VKNOT' and
                curves.token(0, 3) == 'OATF' and
                curves.token(0, 4) == 'GVW' and
                curves.token(0, 5) == 'CLP' and
                curves.token(0, 6) == 'HPTOT_T' and
                curves.token(0, 7) == 'HPMR_T' and
                curves.token(0, 8) == 'HPTR_T'):
            print curves.Line(0)
            print 'token1=', curves.token(0, 1)
            print 'token2=', curves.token(0, 2)
            print 'token3=', curves.token(0, 3)
            print 'token4=', curves.token(0, 4)
            print 'token5=', curves.token(0, 5)
            print 'token6=', curves.token(0, 6)
            print 'token7=', curves.token(0, 7)
            print 'token8=', curves.token(0, 8)
            print 'Error(load_curves): bad header'
            return -1
        n_l = curves.numLines
        d_alt = 0
        for i in range(1, n_l):
            alt = float(curves.token(i, 1))
            if d_alt == 0 or alt > self.alt_t[d_alt - 1]:
                self.alt_t += [alt]
                d_alt += 1
            elif alt < self.alt_t[d_alt - 1]:
                break
        n_vknot = 0
        for j in range(1, n_l):
            vknot = float(curves.token(j, 2))
            if n_vknot == 0 or vknot > self.vknot_t[n_vknot - 1]:
                self.vknot_t += [vknot]
                n_vknot += 1
            elif vknot < self.vknot_t[n_vknot - 1]:
                break
        n_oatf = 0
        for k in range(1, n_l):
            oatf = float(curves.token(k, 3))
            if n_oatf == 0 or oatf > self.oatf_t[n_oatf - 1]:
                self.oatf_t += [oatf]
                n_oatf += 1
            elif oatf < self.oatf_t[n_oatf - 1]:
                break
        n_gvw = 0
        for l in range(1, n_l):
            gvw = float(curves.token(l, 4))
            if n_gvw == 0 or gvw > self.gvw_t[n_gvw - 1]:
                self.gvw_t += [gvw]
                n_gvw += 1
            elif gvw < self.gvw_t[n_gvw - 1]:
                break
        n_clp = 0
        for m in range(1, n_l):
            clp = float(curves.token(m, 5))
            if n_clp == 0 or clp > self.clp_t[n_clp - 1]:
                self.clp_t += [clp]
                n_clp += 1
            elif clp < self.clp_t[n_clp - 1]:
                break
        hptot = []
        hpmr = []
        hptr = []
        for i in range(1, n_l):
            hptot += [float(curves.token(i, 6))]
            hpmr += [float(curves.token(i, 7))]
            # hptr  += [float(curves.token(i, 6)) - float(curves.token(i, 7)) ]
            hptr += [float(curves.token(i, 8))]
        if True:
            print 'alt_t=', self.alt_t
            print 'vknot_t=', self.vknot_t
            print 'oatf_t=', self.oatf_t
            print 'gvw_t=', self.gvw_t
            print 'clp_t=', self.clp_t
            print 'n_l=', n_l
            print 'd_alt=', d_alt, 'n_vknot=', n_vknot, 'n_oatf=', n_oatf, 'n_gvw=', n_gvw, 'n_clp=', n_clp
        hptot_t = []
        hpmr_t = []
        hptr_t = []
        for i in range(d_alt):
            hptotj = []
            hpmrj = []
            hptrj = []
            for j in range(n_vknot):
                hptotk = []
                hpmrk = []
                hptrk = []
                for k in range(n_oatf):
                    hptotl = []
                    hpmrl = []
                    hptrl = []
                    for l in range(n_gvw):
                        hptotm = []
                        hpmrm = []
                        hptrm = []
                        for m in range(n_clp):
                            index = m + (l + (k + (j + i * n_vknot) * n_oatf) * n_gvw) * n_clp
                            hptotm += [hptot[index]]
                            hpmrm += [hpmr[index]]
                            hptrm += [hptr[index]]
                        hptotl += [hptotm]
                        hpmrl += [hpmrm]
                        hptrl += [hptrm]
                    hptotk += [hptotl]
                    hpmrk += [hpmrl]
                    hptrk += [hptrl]
                hptotj += [hptotk]
                hpmrj += [hpmrk]
                hptrj += [hptrk]
            hptot_t += [hptotj]
            hpmr_t += [hpmrj]
            hptr_t += [hptrj]
        self.hptot_0_0.addAxis('x', self.oatf_t)
        self.hptot_0_0.addAxis('y', self.gvw_t)
        self.hptot_0_0.addAxis('z', self.clp_t)
        self.hptot_0_0.setValueTable(hptot_t[0][0])
        self.hptot_0_1.addAxis('x', self.oatf_t)
        self.hptot_0_1.addAxis('y', self.gvw_t)
        self.hptot_0_1.addAxis('z', self.clp_t)
        self.hptot_0_1.setValueTable(hptot_t[0][1])
        self.hptot_1_0.addAxis('x', self.oatf_t)
        self.hptot_1_0.addAxis('y', self.gvw_t)
        self.hptot_1_0.addAxis('z', self.clp_t)
        self.hptot_1_0.setValueTable(hptot_t[1][0])
        self.hptot_1_1.addAxis('x', self.oatf_t)
        self.hptot_1_1.addAxis('y', self.gvw_t)
        self.hptot_1_1.addAxis('z', self.clp_t)
        self.hptot_1_1.setValueTable(hptot_t[1][1])
        self.hptot_2_0.addAxis('x', self.oatf_t)
        self.hptot_2_0.addAxis('y', self.gvw_t)
        self.hptot_2_0.addAxis('z', self.clp_t)
        self.hptot_2_0.setValueTable(hptot_t[2][0])
        self.hptot_2_1.addAxis('x', self.oatf_t)
        self.hptot_2_1.addAxis('y', self.gvw_t)
        self.hptot_2_1.addAxis('z', self.clp_t)
        self.hptot_2_1.setValueTable(hptot_t[2][1])
        self.hpmr_0_0.addAxis('x', self.oatf_t)
        self.hpmr_0_0.addAxis('y', self.gvw_t)
        self.hpmr_0_0.addAxis('z', self.clp_t)
        self.hpmr_0_0.setValueTable(hpmr_t[0][0])
        self.hpmr_0_1.addAxis('x', self.oatf_t)
        self.hpmr_0_1.addAxis('y', self.gvw_t)
        self.hpmr_0_1.addAxis('z', self.clp_t)
        self.hpmr_0_1.setValueTable(hpmr_t[0][1])
        self.hpmr_1_0.addAxis('x', self.oatf_t)
        self.hpmr_1_0.addAxis('y', self.gvw_t)
        self.hpmr_1_0.addAxis('z', self.clp_t)
        self.hpmr_1_0.setValueTable(hpmr_t[1][0])
        self.hpmr_1_1.addAxis('x', self.oatf_t)
        self.hpmr_1_1.addAxis('y', self.gvw_t)
        self.hpmr_1_1.addAxis('z', self.clp_t)
        self.hpmr_1_1.setValueTable(hpmr_t[1][1])
        self.hpmr_2_0.addAxis('x', self.oatf_t)
        self.hpmr_2_0.addAxis('y', self.gvw_t)
        self.hpmr_2_0.addAxis('z', self.clp_t)
        self.hpmr_2_0.setValueTable(hpmr_t[2][0])
        self.hpmr_2_1.addAxis('x', self.oatf_t)
        self.hpmr_2_1.addAxis('y', self.gvw_t)
        self.hpmr_2_1.addAxis('z', self.clp_t)
        self.hpmr_2_1.setValueTable(hpmr_t[2][1])
        self.hptr_0_0.addAxis('x', self.oatf_t)
        self.hptr_0_0.addAxis('y', self.gvw_t)
        self.hptr_0_0.addAxis('z', self.clp_t)
        self.hptr_0_0.setValueTable(hptr_t[0][0])
        self.hptr_0_1.addAxis('x', self.oatf_t)
        self.hptr_0_1.addAxis('y', self.gvw_t)
        self.hptr_0_1.addAxis('z', self.clp_t)
        self.hptr_0_1.setValueTable(hptr_t[0][1])
        self.hptr_1_0.addAxis('x', self.oatf_t)
        self.hptr_1_0.addAxis('y', self.gvw_t)
        self.hptr_1_0.addAxis('z', self.clp_t)
        self.hptr_1_0.setValueTable(hptr_t[1][0])
        self.hptr_1_1.addAxis('x', self.oatf_t)
        self.hptr_1_1.addAxis('y', self.gvw_t)
        self.hptr_1_1.addAxis('z', self.clp_t)
        self.hptr_1_1.setValueTable(hptr_t[1][1])
        self.hptr_2_0.addAxis('x', self.oatf_t)
        self.hptr_2_0.addAxis('y', self.gvw_t)
        self.hptr_2_0.addAxis('z', self.clp_t)
        self.hptr_2_0.setValueTable(hptr_t[2][0])
        self.hptr_2_1.addAxis('x', self.oatf_t)
        self.hptr_2_1.addAxis('y', self.gvw_t)
        self.hptr_2_1.addAxis('z', self.clp_t)
        self.hptr_2_1.setValueTable(hptr_t[2][1])
        self.hptot = hptot
        self.hpmr = hpmr
        self.hptr = hptr

    def load_lookup(self, alt, vknot, oatf, gvw, dynang):
        """Perform 5-D table lookup for rotor loads (extrapolates)"""
        self.alt = alt
        self.vknot = vknot
        self.oatf = oatf
        self.gvw = gvw
        self.dynang = dynang
        hptot_0kts_0ft = self.hptot_0_0.lookup(x=oatf, y=gvw, z=dynang)
        hptot_0kts_3kft = self.hptot_0_1.lookup(x=oatf, y=gvw, z=dynang)
        hptot_80kts_0ft = self.hptot_1_0.lookup(x=oatf, y=gvw, z=dynang)
        hptot_80kts_3kft = self.hptot_1_1.lookup(x=oatf, y=gvw, z=dynang)
        hptot_160kts_0ft = self.hptot_2_0.lookup(x=oatf, y=gvw, z=dynang)
        hptot_160kts_3kft = self.hptot_2_1.lookup(x=oatf, y=gvw, z=dynang)

        hpmr_0kts_0ft = self.hpmr_0_0.lookup(x=oatf, y=gvw, z=dynang)
        hpmr_0kts_3kft = self.hpmr_0_1.lookup(x=oatf, y=gvw, z=dynang)
        hpmr_80kts_0ft = self.hpmr_1_0.lookup(x=oatf, y=gvw, z=dynang)
        hpmr_80kts_3kft = self.hpmr_1_1.lookup(x=oatf, y=gvw, z=dynang)
        hpmr_160kts_0ft = self.hpmr_2_0.lookup(x=oatf, y=gvw, z=dynang)
        hpmr_160kts_3kft = self.hpmr_2_1.lookup(x=oatf, y=gvw, z=dynang)

        hptr_0kts_0ft = self.hptr_0_0.lookup(x=oatf, y=gvw, z=dynang)
        hptr_0kts_3kft = self.hptr_0_1.lookup(x=oatf, y=gvw, z=dynang)
        hptr_80kts_0ft = self.hptr_1_0.lookup(x=oatf, y=gvw, z=dynang)
        hptr_80kts_3kft = self.hptr_1_1.lookup(x=oatf, y=gvw, z=dynang)
        hptr_160kts_0ft = self.hptr_2_0.lookup(x=oatf, y=gvw, z=dynang)
        hptr_160kts_3kft = self.hptr_2_1.lookup(x=oatf, y=gvw, z=dynang)

        if vknot < self.vknot_t[1]:
            hptotv0 = (vknot - self.vknot_t[0]) / (self.vknot_t[1] - self.vknot_t[0]) * (
                        hptot_80kts_0ft - hptot_0kts_0ft) + hptot_0kts_0ft
            hptotv1 = (vknot - self.vknot_t[0]) / (self.vknot_t[1] - self.vknot_t[0]) * (
                        hptot_80kts_3kft - hptot_0kts_3kft) + hptot_0kts_3kft
            hpmrv0 = (vknot - self.vknot_t[0]) / (self.vknot_t[1] - self.vknot_t[0]) * (
                        hpmr_80kts_0ft - hpmr_0kts_0ft) + hpmr_0kts_0ft
            hpmrv1 = (vknot - self.vknot_t[0]) / (self.vknot_t[1] - self.vknot_t[0]) * (
                        hpmr_80kts_3kft - hpmr_0kts_3kft) + hpmr_0kts_3kft
            hptrv0 = (vknot - self.vknot_t[0]) / (self.vknot_t[1] - self.vknot_t[0]) * (
                        hptr_80kts_0ft - hptr_0kts_0ft) + hptr_0kts_0ft
            hptrv1 = (vknot - self.vknot_t[0]) / (self.vknot_t[1] - self.vknot_t[0]) * (
                        hptr_80kts_3kft - hptr_0kts_3kft) + hptr_0kts_3kft
        else:
            hptotv0 = (vknot - self.vknot_t[1]) / (self.vknot_t[2] - self.vknot_t[1]) * (
                        hptot_160kts_0ft - hptot_80kts_0ft) + hptot_80kts_0ft
            hptotv1 = (vknot - self.vknot_t[1]) / (self.vknot_t[2] - self.vknot_t[1]) * (
                        hptot_160kts_3kft - hptot_80kts_3kft) + hptot_80kts_3kft
            hpmrv0 = (vknot - self.vknot_t[1]) / (self.vknot_t[2] - self.vknot_t[1]) * (
                        hpmr_160kts_0ft - hpmr_80kts_0ft) + hpmr_80kts_0ft
            hpmrv1 = (vknot - self.vknot_t[1]) / (self.vknot_t[2] - self.vknot_t[1]) * (
                        hpmr_160kts_3kft - hpmr_80kts_3kft) + hpmr_80kts_3kft
            hptrv0 = (vknot - self.vknot_t[1]) / (self.vknot_t[2] - self.vknot_t[1]) * (
                        hptr_160kts_0ft - hptr_80kts_0ft) + hptr_80kts_0ft
            hptrv1 = (vknot - self.vknot_t[1]) / (self.vknot_t[2] - self.vknot_t[1]) * (
                        hptr_160kts_3kft - hptr_80kts_3kft) + hptr_80kts_3kft
        self.hptot = (alt - self.alt_t[0]) / (self.alt_t[1] - self.alt_t[0]) * (hptotv1 - hptotv0) + hptotv0
        self.hpmr = (alt - self.alt_t[0]) / (self.alt_t[1] - self.alt_t[0]) * (hpmrv1 - hpmrv0) + hpmrv0
        self.hptr = (alt - self.alt_t[0]) / (self.alt_t[1] - self.alt_t[0]) * (hptrv1 - hptrv0) + hptrv0
        self.qtotload = self.hptot / self.n_mr * 5252.1131
        self.qmrload = self.hpmr / self.n_mr * 5252.1131
        self.qtrload = self.hptr / self.n_tr * 5252.1131
        return self.qtotload, self.qmrload, self.qtrload

    def update(self):
        self.n_mr = self.y[0]
        self.n_tr = self.y[1]
        self.nt = self.y[2]
        self.n1 = self.y[3]
        self.n2 = self.y[4]
        self.n3 = self.y[5]
        self.qmr = self.y[6]
        self.qtr = self.y[7]
        self.q1 = self.y[8]
        self.q2 = self.y[9]
        self.q3 = self.y[10]
        self.count += 1
        self.time = self.count * self.d_time
        self.yp = [x for x in self.y]

    def __repr__(self):
        """Print result"""
        if 1 == self.count:
            cout = 'time, alt, vknot, gvw, dynang, n_mr, n_tr, nt, n1, n2, n3, qmr, qtr, q1, q2, q3, qgas1, qgas2,' + \
                   'qgas3, qtotload, qmrload, qtrload\n'
        else:
            cout = ''
        if self.count % 1 == 0 or self.count == 1:
            cout += '%(time)g, %(alt)g, %(vknot)g, %(gvw)g, %(dynang)g, %(n_mr)g, %(n_tr)g, %(nt)g, %(n1)g, %(n2)g, \
                     %(n3)g, %(qmr)g, %(qtr)g, %(q1)g, %(q2)g, %(q3)g, %(qgas1)g, %(qgas2)g, %(qgas3)g, %(qtotload)g, \
                     %(qmrload)g, %(qtrload)g,\n' \
                     % {'time': self.time - self.d_time, 'alt': self.alt, 'vknot': self.vknot, 'gvw': self.gvw,
                        'dynang': self.dynang, 'n_mr': self.n_mr, 'n_tr': self.n_tr, 'nt': self.nt, 'n1': self.n1,
                        'n2': self.n2, 'n3': self.n3,
                        'qmr': self.qmr, 'qtr': self.qtr, 'q1': self.q1, 'q2': self.q2, 'q3': self.q3,
                        'qgas1': self.qgas1, 'qgas2': self.qgas2, 'qgas3': self.qgas3, 'qtotload': self.qtotload,
                        'qmrload': self.qmrload, 'qtrload': self.qtrload, }
        return cout


def main():
    # noinspection PyUnresolvedReferences
    import rotorModel
    # Initial inputs
    # d_qload = 0
    zdynang = 70
    alt = 3000
    vknot = 0.01
    oatf = 59
    gvw = 46000
    final_time = 30
    d_time = 0.006

    # Setup the rotor model
    r_m = rotorModel.SimpleThreeEngineRotor(d_time)

    if r_m.load_curves() == -1:
        print 'failed to load rotorCurves'
        return -1

    r_m.write_curves()

    # Executive initialization
    nomnp = r_m.nomnp
    i = 0
    results_file = file('rotorModel.csv', 'wb')

    # Rotor initialization
    (qtotload, qmrload, qtrload) = r_m.load_lookup(alt, vknot, oatf, gvw, zdynang)
    q_total_actual = qmrload + qtrload
    qgas1 = q_total_actual / 3
    qgas2 = q_total_actual / 3
    qgas3 = q_total_actual / 3
    r_m.assign_states(nomnp, qmrload, qtrload, qgas1, qgas2, qgas3)

    # Main time loop
    while True:
        time = i * d_time

        # Collective input
        if 8 > time > 5:
            ddynang = 10
        elif 11 > time > 8:
            ddynang = -10
        else:
            ddynang = 0
        ddynang = 0
        dynang = zdynang + ddynang

        # Lookup load model
        (qtotload, qmrload, qtrload) = r_m.load_lookup(alt, vknot, oatf, gvw, dynang)

        # Assign inputs to rotor object
        r_m.assign_inputs(qmrload, qtrload, qgas1, qgas2, qgas3)

        # Integrate and update the rotor object
        ode.rk4(r_m, d_time)
        r_m.update()

        # Write results
        pcnr = r_m.n_mr / nomnp * 100
        results_file.write(r_m.__repr__())
        if final_time <= time:
            break
        i += 1

    print 'time=', time, 'vknot=', vknot, 'alt=', alt, 'pcnr=', pcnr, 'gvw=', gvw, 'clp=', zdynang


if __name__ == '__main__':
    sys.exit(main())
    # sys.exit(cProfile.run("main()"))
