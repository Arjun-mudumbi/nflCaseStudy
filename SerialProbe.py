# -*- coding: utf-8 -*-
"""
Created on Wed Apr 18 10:47:45 2018

@author: Arjun Mudumbi
"""
#%%% import all the required packages
import numpy as np
import pandas as pd
from gurobipy import *
import sqlite3
#%%% read the file
NFL=read("NFL.lp")
#%%%%extract the variables and constraints
v=NFL.getVars()
myConstrs=NFL.getConstrs()
mygamelist=[]
games={}
for c in myConstrs:
    row =NFL.getRow(c)
    myFlag=True
    for r in range(row.size()):            
        if row.getVar(r).varName[:2] !="GO":
            myFlag=False
        if myFlag==True:
            mygamelist.append(row.getVar(r).varName[2:].split("_"))
            games[row.getVar(r).varName] = row.getVar(r)
mygamelist=pd.DataFrame(mygamelist)
mygamelist=mygamelist.iloc[:,1:]
mygamelist=mygamelist.drop_duplicates()
names=["Away","Home","Day","Slot","Network","Week"]
mygamelist.columns=["Away","Home","Day","Slot","Network","Week"]
mygamelist=mygamelist.sort_values(by=names)
varbounds={}
le=len(mygamelist)
for i in range(le):
    varbounds[mygamelist.iloc[i,0],mygamelist.iloc[i,1],mygamelist.iloc[i,2],mygamelist.iloc[i,3],mygamelist.iloc[i,4],mygamelist.iloc[i,5]]=[0,1]
#%%%set varbounds 0 for the values with zero rhs
for c in myConstrs:
    if c.Sense == '<' and c.RHS == 0:
        row = NFL.getRow(c)
        myFlag=True
        for r in range(row.size()):            
            if row.getVar(r).varName[:2] !="GO":
                myFlag=False
            if myFlag==True:
                row.getVar(r).lb = 0
                row.getVar(r).ub = 0
                NFL.update()
                games[row.getVar(r).varName].lb=0
                games[row.getVar(r).varName].ub=0
                NFL.update()
                e,a,h,d,s,n,w=row.getVar(r).varName[2:].split("_")
                varbounds[a,h,d,s,n,w][0]=0
                varbounds[a,h,d,s,n,w][1]=0

#%%%
NFL.setParam("TimeLimit",8)
myFlag=True
while(myFlag):
    myFlag=False
    for v in games:
        if games[v].lb !=games[v].ub and 'PRIME' in v:
            games[v].lb=1
            games[v].ub=1
            NFL.update()
            NFL.optimize()
            if NFL.status == GRB.INFEASIBLE:
                print("Infeasible")
                games[v].lb=0
                games[v].ub=0
                e,a,h,d,s,n,w=v.split("_")
                varbounds[a,h,d,s,n,w][0]=0
                varbounds[a,h,d,s,n,w][1]=0
                myFlag=True
            else:
                print("Feasible")
                games[v].lb=0
                games[v].ub=1
                e,a,h,d,s,n,w=v.split("_")
                varbounds[a,h,d,s,n,w][0]=0
                varbounds[a,h,d,s,n,w][1]=1
            NFL.update()
#%%%
NFL.write("output.lp")
var=[]
for v in varbounds:
    a=v[0]
    h=v[1]
    d=v[2]
    s=v[3]
    n=v[4]
    w=v[5]   
    b1=varbounds[v][0]
    b2=varbounds[v][1]
    v2=[a,h,d,s,w,n,b1,b2]
    var.append(v2)
var=pd.DataFrame(var)
var.to_csv("var.csv",index=False)                           
#%%%%
prime=[]
for v in varbounds:
    if v[3]=="PRIME":
        a=v[0]
        h=v[1]
        d=v[2]
        s=v[3]
        n=v[4]
        w=v[5]   
        b1=varbounds[v][0]
        b2=varbounds[v][1]
        v2=[a,h,d,s,w,n,b1,b2]
        prime.append(v2)
prime=pd.DataFrame(prime)
prime.to_csv("prime.csv",index=False) 
                            
                
                        
                        
        
            
        
    