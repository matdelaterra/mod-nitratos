# -*- coding: utf-8 -*-
"""
Created on Thu Feb  6 14:31:28 2020

@author: Jorge Antonio Matías López
"""

## Modelo transporte de nitratos V3
'''
En esta versión se van a manejar los atributos del objeto dentro de un dataFrame de pandas
si es conveniente se comenzará con el desarrollo de una interfaz gráfica en Tkinter, así como 
la lógica para utilizar capas diferentes
'''
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math

##Orientado a objetos, el objeto es modelo 
class Modelo:
    def __init__(self, D=100, dz=1, propiedades=None, NH4=60, NO3=0.1):
        
        self.NH4 = NH4
        self.NO3 = NO3
        self.profundidad = D 
        self.incremento = dz   
        self.propiedades = propiedades
        self.vz = propiedades['HLR']/propiedades['qs'] # CTE
        self.Td = self.incremento/self.vz #cte
        self.__df_salida = None
        self.__p_profundidad = None
        self.__p_presion =  None
        self.__p_humedad = None
        self.__cont_carbon = None
        self.WFP = None
        self.R = None
        self.krmax = None
        self.Vmax = None
        self.C_NH4 = None
        self.C_NO3 = None
        self.Ctotal = None
        self.__allow_graph = False
 
    
    def perfil_z(self):### Perfil de profundidad
        profundidad = self.profundidad
        incremento = self.incremento
        prof = np.linspace(0, profundidad, int(profundidad//incremento)+1)
        self.__p_profundidad = prof
        self.__df_salida = pd.DataFrame(data = prof, columns = ['z'])
        return prof
    
    
    def presion(self, Yo=0): ## Perfil de presión
        dz = self.incremento
        psi = np.zeros(len(self.__p_profundidad))
        propiedades = self.propiedades
        aG = propiedades['aG']
        #Yo = propiedades['Yo']
        Ks = propiedades['Ks']
        HLR = propiedades['HLR']
        
        for ind, val in enumerate(psi):
            psi[ind] = Yo
            log = (HLR/Ks) * math.exp(-aG*Yo) * (math.exp(aG*dz) - 1) + 1
            Yo = Yo - dz + (1/aG) * math.log(log)
        self.__p_presion = psi
        return psi
    
    
    def tetha(self):####### Perfil de humedad
        presion = self.__p_presion
        aVG = self.propiedades['aVG']
        qs = self.propiedades['qs']
        qr = self.propiedades['qr']
        n = self.propiedades['n']
        m = 1 - 1/n
        #print(aVG, qs, qr,n,m, sep='\n')
        tetha = np.zeros(presion.shape[0])
        
        for ind, val in enumerate(presion):
            if val > 0:
                tetha[ind] = qs   
            else:
                ss = qr + (qs-qr)/ math.pow((1 + math.pow(abs(aVG*val),n)),m)
                tetha[ind] = ss
        self.__p_humedad = tetha
        return tetha


    def fWFP(self):### intentar con map fWFP(self, hum)
        
        qs = self.propiedades['qs']
        swp = self.propiedades['swp']
        hum = self.__p_humedad
        WFP = np.zeros(len(hum))
        for i, tetha in enumerate(hum):
            sw = tetha/qs
            if sw > swp:
                WFP[i] = sw
            else:
                WFP[i] = swp
        self.WFP = WFP
        return WFP
    
    
    def fcont_c(self):
        ac =  self.propiedades['ac']
        cont_c = np.zeros(len(self.__p_profundidad))
        for i, z in enumerate(self.__p_profundidad):
            cont_c[i] = math.exp(-ac*z)
        self.__cont_carbon = cont_c
        self.__df_salida['fz'] = np.flip(cont_c)
        return cont_c
    
    
    def fswnt(self):
        WFP = self.WFP
        fs = self.propiedades['fs']
        fwp = self.propiedades['fwp']
        swp = self.propiedades['swp']
        e2 = self.propiedades['e2']	 # e2
        e3 = self.propiedades['e3']
        sl = self.propiedades['sl']
        sh = self.propiedades['sh']
        
        fsw_nt = np.zeros(len(WFP))
        
        for i, wfp in enumerate(WFP):
            if sh < wfp <= 1:
                fsw_nt[i] = fs + (1-fs)*math.pow((1-wfp)/(1-sh),e2)
            elif sl <= wfp <= sh:
                fsw_nt[i] = 1
            elif swp <= wfp <= sl:
                fsw_nt[i] = fwp + (1-fwp)*math.pow((wfp-swp)/(sl-swp),e3)
        self.fsw_nt = fsw_nt
        self.__df_salida['fsw_nt'] = np.flip(fsw_nt)
        return fsw_nt
        
      
    def fswdnt(self):
        WFP = self.WFP
        sdn = self.propiedades['sdn']
        ednt = self.propiedades['ednt']
        
        fsw_dnt = np.zeros(len(WFP))
        
        for i, wfp in enumerate(WFP):
            if wfp < sdn:
                fsw_dnt[i] = 0
            else:
                fsw_dnt[i] = math.pow((wfp-sdn)/(1-sdn),ednt)
        self.fsw_dnt = fsw_dnt
        self.__df_salida['fsw_dnt'] = np.flip(fsw_dnt)
        return fsw_dnt
    
 ##### Parámetros que se utilizan en el calculo de C   
    def fR(self):
        kd = self.propiedades['kd']
        tetha = self.__p_humedad
        rho =  self.propiedades['rho']
        r = np.zeros(len(tetha))
        
        for i, h in enumerate(tetha):
            r[i] = 1 + (rho*kd/(h))
        self.R = r
        self.__df_salida['R'] = np.flip(r)
        return r
    
    def f_krmax(self):
        kr_max = self.propiedades['kr_max']
        kr = self.fsw_nt * kr_max
        self.krmax = kr
        self.__df_salida['krmax'] = np.flip(kr)
        return kr
    
    
    def fVmax(self):
        Vmax = self.propiedades['Vmax']
        Vm = self.fsw_dnt * Vmax
        self.Vmax = Vm
        self.__df_salida['Vmax'] = np.flip(Vm)
        return Vm
    
    
###################    
    def fconc(self, km, Co, mu_max, R=1, fz=1):
        td = self.Td
        ## Newton rhapson
        ini = 0.000001
        b = -Co-km*math.log(Co) + R*mu_max*fz*td
        con = lambda c,b, km : c + km * math.log(c) + b
        der_con = lambda c, km: 1 + km/c
        
        it = 1
        while True:
            nv = ini - con(ini,b,km)/der_con(ini,km)
            if abs(ini - nv) < 0.0000001 or it > 50:
                conc = nv
                break
            else:
                ini = nv
                it += 1
        return conc
    

    def Cnit(self):
        #parametros
        C_ini_NH4 = self.NH4
        C_ini_NO3 = self.NO3
        R_nt = self.__df_salida['R']
        krmax = self.__df_salida['krmax']
        vmax = self.__df_salida['Vmax']       
        
        n = np.shape(self.__p_profundidad)[0] 
        c_NH4 = np.zeros(n)
        c_NH4[0] = C_ini_NH4
        c_NO3 = np.zeros(n)
        c_NO3[0] = C_ini_NO3
        
        for i in range(1,n):
            if C_ini_NH4 > 0.001:
                c_NH4[i] = self.fconc(self.propiedades['Km_nit'], C_ini_NH4, krmax[i], R_nt[i])
            else:
                c_NH4[i] = 0
            
            C_ini_NH4 = c_NH4[i]
            
            C_ini_NO3 = c_NO3[i-1] + c_NH4[i-1] - c_NH4[i]
    
            c_NO3[i] = self.fconc( self.propiedades['Km_dnt'],C_ini_NO3, vmax[i])
            
        self.C_NH4 = c_NH4
        self.__df_salida['cNH4'] = c_NH4
        self.C_NO3 = c_NO3
        self.__df_salida['cNO3'] = c_NO3
        self.Ctotal = c_NH4 + c_NO3    
        self.__df_salida['Total N'] = self.Ctotal
        
        #Flujo de masa
        Ctotal = self.Ctotal
        hlr = self.propiedades['HLR']
        mass_fl = np.zeros(Ctotal.shape[0])
        for i in range(Ctotal.shape[0]):
            mass_fl[i] = (2/3) * Ctotal[i]* (2/3) * hlr / 100
        
        self.mass_fl = mass_fl
            
            
    def run(self):
        #cálculo de profundidad
        self.perfil_z()
        #### HIDRAULICA Y CONTENIDO DE HUMEDAD
        #Cálculo de presiones
        self.presion()# = 
        #perfil de humedad
        self.tetha()
        #WFP
        self.fWFP()
        #FACTORES PARA LAS REACCIONES
        ## efecto del contenido de carbono
        self.fcont_c()
        ## efecto de sw en la nit
        self.fswnt()
        ## efecto de sw en la desn
        self.fswdnt()
        
        #ELEMENTOS PARA CALCULAR LAS CONCENTRACIONES
        ### factor de retardación
        self.fR()
        ### kr max
        self.f_krmax()
        ##Vmax
        self.fVmax()
        ## Concentraciones
        self.Cnit()
        
        self.__allow_graph = True
            
    def graficar(self):
        if self.__allow_graph:
            x = self.__p_profundidad
            y1 = self.C_NH4
            y2 = self.C_NO3
            y3 = self.Ctotal
            y_fl = self.mass_fl
            
            
            fig, ax = plt.subplots()
            ax.plot(x, y1)
            ax.plot(x, y2)
            ax.plot(x, y3)
            ax.set_xlabel('Profundidad')
            ax.set_ylabel('Concentración')
            ax.set_title('Concentración N')
            ax.legend(['CNH4','CNO3','CTotal'])
            
    
            fig1, ax1 = plt.subplots()
            ax1.plot(x, y_fl)
            ax1.set_xlabel('Profundidad')
            ax1.set_ylabel('Mass flux $gm^2 d^{-1}$')
            ax1.set_title('Mass Flux TN')
            ax1.legend(['Mass Flux TN'])
            plt.show()
        else:
            print('Se debe ejecutar el modelo')
        
        

#Diccionario de propiedades
dic_h = {
'HLR':5.00,
'aG':0.025,#	 aG
'aVG':0.015,#	aVG
'Ks':14.75,#	Ks
#'Yo':0,#	Yo
'qr':0.0980,#	qr
'qs':0.459,#	qs 
'n':1.26,#	n 
'l':0.50,	#  l 
######## nit
'swp':0.15,# swp ### sirve para calcular WFP
'fs':0.00,#	  fs 
'fwp':0.00,#	  fwp
'e2':2.27,	 # e2
'e3':1.10,	#  e3 
'kr_max':50.00,#	  kr max
'Km_nit':5.00,#3	  Km,nit
'bnit':0.35,#	  bnit 
'sl':0.67,#	 sl
'sh':0.81,#	  sh
####### dnt
'ednt':3.77,#	  ednt
'Vmax':2.56,#	  Vmax 
'Km_dnt':5.00,#	  Km,dnt
'bdnt':0.35,#	  bdnt 
'sdn':0.00,#	  sdn 
'ac':0.00,#	  ac 
##### R
'kd':1.46,
'rho':1.50	  #rho
}

#Creación del objeto modelo
mod = Modelo(120, 1, propiedades=dic_h, NH4=60, NO3 = 1)

#cálculo de profundidad
# z = mod.perfil_z()
# #### HIDRAULICA Y CONTENIDO DE HUMEDAD
# #Cálculo de presiones
# y = mod.presion()# = 
# #perfil de humedad
# hum = mod.tetha()
# #WFP
# WFP = mod.fWFP()
# #FACTORES PARA LAS REACCIONES
# ## efecto del contenido de carbono
# fz = mod.fcont_c()
# ## efecto de sw en la nit
# fswnt = mod.fswnt()
# ## efecto de sw en la desn
# fswdnt = mod.fswdnt()


# #ELEMENTOS PARA CALCULAR LAS CONCENTRACIONES
# ### factor de retardación

# R = mod.fR()
# ### kr max
# krmax = mod.f_krmax()
# ##Vmax
# Vmax = mod.fVmax()

## Concentraciones
# mod.Cnit()

# CO3 = mod.C_NO3
# CNH4 = mod.C_NH4
# #
# mod.graficar()