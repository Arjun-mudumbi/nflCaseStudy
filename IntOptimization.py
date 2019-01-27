import csv
import sqlite3
from gurobipy import *
import pandas as pd
#%%%%create a database to hold information
teamdata= pd.read_csv("teamdata.csv")
gamavar= pd.read_csv("GameVariables_2018.csv")
myconn=sqlite3.connect('nfl.db')
teamdata.to_sql(name="teamdata",con=myconn,if_exists="replace")
#%%
gamavar.to_sql(name="game",con=myconn,if_exists="replace")

#%%% import teams csv

conf=teamdata.groupby(by="CONF")
conference={}
for x in conf.groups:
    conference[x]=(conf.get_group(x))
nfc=conference["NFC"]
afc=conference["AFC"]
conference["NFC"]=list(nfc["TEAM"])
conference["AFC"]=list(afc["TEAM"])
#%% create a division
division={}
div={}
dis=nfc.groupby(by="DIV")
for y in dis.groups:
    div[y]=(dis.get_group(y))
for y in div:
    div[y]=div[y]["TEAM"]
    division["NFC"]=div
#%%
dip={}
dit=afc.groupby(by="DIV")
for z in dit.groups:
    dip[z]=(dit.get_group(z))
for z in dip:
    dip[z]=dip[z]["TEAM"]
    division["AFC"]=dip
del div
del dip
#%%
GameData={}
with open("Game.csv", "r") as myCSV:
    myReader = csv.reader(myCSV)
    for row in myReader:
        GameData[row[0],row[1],row[2],row[3],row[4]]=float(row[5])
#%% build model
NFL = Model()
NFL.modelSense = GRB.MAXIMIZE
NFL.update()
#%% objective function
Games = {}

for game in GameData:
    a = game[0]
    h = game[1]
    w = game[2]
    s = game[3]
    n = game[4]
    q = GameData[game]
    Games[game] = NFL.addVar(obj = q,
                              vtype = GRB.BINARY,
                              name = 'x(%s)' % ','.join(game))
#%% create gurobi specific tuple lists so we can incorporate wildcards
gamelist = []
for a,h,w,s,n in GameData:
    gamelist.append((a,h,w,s,n))
gamelist = tuplelist(gamelist)
#%%
#%% create constraints         
myConstrs = {}

#%%% create a team list
away = {}
home = {}
team = []
away2={}

for a,h,w,s,n in GameData:
    if a not in away:
        away[a] = []
    if h not in away[a]:
        away[a].append(h)
    if h not in home and h != 'BYE':        
        home[h] = []
    if h != 'BYE':
        if a not in home[h]:
            home[h].append(a)
    if a not in team:
        team.append(a)
for a,h,w,s,n in GameData:
    if a not in away2:
        away2[a] = []
    if h not in away2[a] and h!="BYE":
        away2[a].append(h)
        
#%%each team can only play at home against another team that is away, once
for a in team:
    for h in away[a]:
        Cname='01_Game_Once_%s_%s' % (a,h)
        myConstrs[Cname]= NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(a,h,'*','*','*'))==1,
                                        name = Cname)
NFL.update()


#%%each team can only play once a week
for t in team:
    for w in range (1,18):
        Cname = '02_Each_Once_%s_%s' % (t,w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w),'*','*')) + quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w),'*','*'))==1,
                                         name = Cname)

NFL.update()

#%%%List comprehension in python
## week =str(x) for x in range(1,18)
## for t in team:
#    for w in range (1,18):
#        Cname = '02_Each_Once_%s_%s' % (t,n)
#        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',w,'*','*')) + quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,w,'*','*'))==1,
#                                         name = Cname)
#
#NFL.update()
#%%%Bye games is only played in week 4-12 
#Handled by the Dataset imported
#Dataset removed the Bye games in rest of the weeks
#for t in team:
#    for w in range(1,18):
#        Cname = '03_BYE_Once_%s_%s' % (t,n)
#        if w in range (4,12):
#            myConstrs[Cname]=NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n, in gamelist.select(t,"bye",w,"*","*"))==1,name=Cname)
#        else:
#            myConstrs[Cname]=NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n, in gamelist.select(t,"bye",w,"*","*"))==0,name=Cname)
#NFL.update()

#%%%No more than 6 byes in a week
for w in range(4,12):
    Cname = '04_BYE_6_%s'%w
    myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','BYE',str(w),'SUNB','BYE')) <=6,
                                         name = Cname)    
NFL.update()

#%%%No early BYE for Miami and Tampa Bay
for t in team:
    for w in range (4,12):
        if((t=="MIA" or t=="TB") and w==4):
            Cname = '05_NO_EARLY_BYES_%s_%s' % (t,w)
            myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'BYE',str(w),'SUNB','BYE')) ==0,
                                         name = Cname)           

NFL.update()


#%%%% One thursday night game per week untill week 16
#This is actually taken care in data as the data doesnt allow 
for w in range (1,18):
    if(w in range(1,17)):
        Cname = '06_ONE_THURSDAYNIGHT_%s' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'THUN','*')) ==1,
                                     name = Cname)
    else:
        Cname = '06_ONE_THURSDAYNIGHT_%s' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'THUN','*')) ==0,
                                     name = Cname)
NFL.update()

#%%%Sat early and Sat late games in week 16
#Even this taken care by data 
for w in range (1,18):
    if(w==16):
        Cname = '07A_WEEK16_SATSLOT_%s_SATL' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'SATL','*')) ==1,
                                     name = Cname)
        Cname = '07B_WEEK16_SATSLOT_%s_SATE' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'SATE','*')) ==1,
                                     name = Cname)
    else:
        Cname = '07A_WEEK16_SATSLOT_%s_SATL' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'SATL','*')) ==0,
                                     name = Cname)
        Cname = '07B_WEEK16_SATSLOT_%s_SATE' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'SATE','*')) ==0,
                                     name = Cname)
NFL.update()

#%%%Sunday only one double header game
for w in range (1,18):
    if(w in range(1,16)):
        Cname = '08_ONE_SUNDAYDOUBLEHEADER_%s' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'SUND','*')) ==1,
                                     name = Cname)
    else:
        Cname = '08_ONE_SUNDAYDOUBLEHEADER_%s' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'SUND','*')) ==2,
                                     name = Cname)
NFL.update()

#%%%Sunday night only 1 game
for w in range (1,18):
    if(w in range(1,17)):
        Cname = '09_ONE_SUNDAYNIGHT_%s' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'SUNN','*')) ==1,
                                     name = Cname)
    else:
        Cname = '09_ONE_SUNDAYNIGHT_%s' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'SUNN','*')) ==0,
                                     name = Cname)
NFL.update()

#%%%Monday night games
# MON2 only occurs during week 1
westcoast=list(teamdata.loc[teamdata["TIMEZONE"]==4,"TEAM"])
notwestcoast=list(teamdata.loc[teamdata["TIMEZONE"]!=4,"TEAM"])

for w in range(1,18):
    if(w==1):
        Cname = '10A_ONE_EARLY_MONDAYNIGHT_%s' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'MON1','*')) ==1,
                                     name = Cname)
        Cname = '10A_WEST_COST_MONDAY_LATE_%s' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',westcoast,str(w),'MON2','*')) ==1,
                                     name = Cname)
    elif(2<=w<=16):
        Cname = '10B_ONE_MONDAYNIGHT_%s' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'MON1','*')) ==1,
                                     name = Cname)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'MON2','*')) ==0,
                                     name = Cname)
    else:
        Cname = '10C_ONE_MONDAYNIGHT_%s' % (w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'MON1','*')) ==0,
                                     name = Cname)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*','*',str(w),'MON2','*')) ==0,
                                     name = Cname)
    
    
NFL.update()
#%%west coast team and mountain team cannot play early sun game
mountain=list(teamdata.loc[teamdata["TIMEZONE"]==3,"TEAM"])
nosune= westcoast+mountain
for t in nosune:
    Cname="11_NO_SUN_EARLY_FOR_%s"%(t)
    myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,"*",'SUNE','*')) ==0,
                                     name = Cname)
NFL.update()
#%%no team plays four consecutive home/away games 
for t in team:
    for w in range(1,15):
        Cname="12A_NO_CONSECUTIVEHOMEGAMES_%s"%(t)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+1),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+2),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+3),'*','*'))<=3,
                                     name = Cname)
        Cname="12B_NO_CONSECUTIVEAWAYGAMES_%s"%(t)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+1),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+2),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+3),'*','*'))<=3,
                                     name = Cname)
NFL.update()

#%%%Atleast 2 home/Away games in 6 matches
for t in team:
    for w in range(1,13):
        Cname="13A_ATLEAST_2HOMEGAMES_6WEEKS_%s_%s"%(t,w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+1),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+2),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+3),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+4),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+5),'*','*'))>=2,
                                         name = Cname)
        Cname="13A_ATLEAST_2AWAYGAMES_6WEEKS_%s_%s"%(t,w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+1),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+2),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+3),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+4),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+5),'*','*'))>=2,
                                     name = Cname)
NFL.update()

#%%%
for t in team:
    for w in range(1,8):
        Cname="14A_ATLEAST_4HOMEGAMES_10WEEKS_%s_%s"%(t,w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+1),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+2),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+3),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+4),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+5),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+6),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+7),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+8),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+9),'*','*'))>=4,
                                         name = Cname)
        Cname="14B_ATLEAST_4AWAYGAMES_10WEEKS_%s_%s"%(t,w)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+1),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+2),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+3),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+4),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+5),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+6),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+7),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+8),'*','*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+9),'*','*'))>=4,
                                     name = Cname)
NFL.update()

#%%%%Thursday night game players are home the week before
for t in team:
    for w in range(1,17):
         Cname="15_THURSDAYNIGHT_HOMEWEEKBEFORE_%s"%(t)
         myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w),'*','*'))+
                                          quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+1),'THUN','*'))<=1,
                                     name = Cname)
NFL.update()
#%%%no teams plays 2 road games coming off bye
Link_16 = {}
for t in team:
    for a in away[t]:
        if a != "BYE":
            for w in range(5,13):
                Lname = 'Link_16_%s_%s_%s' % (t,a,w)
                Link_16[t,a,str(w)] = NFL.addVar(obj = 0, vtype = GRB.BINARY, name = Lname)             
NFL.update()

for t in team:
    for a in away[t]:
        if a != "BYE":
            CName = '16A_no_more_than_2_after_BYE_%s_%s_%s' % (t,a,w)
            myConstrs[CName] = NFL.addConstr(quicksum(Link_16[t,a,str(w)]for w in range(5,13)) <= 1,name = CName)
NFL.update()
for t in team:
    for a in away[t]:
        if a != "BYE":
            for w in range(4,12):
                CName = '16B_no_more_than_2_after_BYE_%s_%s_%s' % (t,a,w)
                myConstrs[CName] = NFL.addConstr(Games[t,'BYE',str(w),'SUNB','BYE'] + quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(a,t,str(w+1),'*','*')) <= 1+Link_16[t,a,str(w+1)],name = CName)
NFL.update()
#%%%%c17
pen17a = {}
pen17b = {}
for t in team:
    for w in range(4,15):
        Vname = 'pen17a_%s_%s' % (t,w)
        pen17a[t,str(w)] = NFL.addVar(obj = -4, vtype = GRB.BINARY, name = Vname)
NFL.update()
for t in team:
    for w in range(4,15):
        Vname = 'pen17b_%s_%s' % (t,w)
        pen17b[t,str(w)] = NFL.addVar(obj = -4, vtype = GRB.BINARY, name = Vname)
NFL.update()
for t in team:
    for w in range(4,15):
        Cname="17A_NO_CONSECUTIVEHOMEGAMES_%s"%(t)
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+1),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select('*',t,str(w+2),'*','*'))<=2+pen17a[t,str(w)],
                                     name = Cname)
        CName="17B_NO_CONSECUTIVEAWAYGAMES_%s"%(t)
        myConstrs[CName] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+1),"*",'*'))+
                                         quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(t,'*',str(w+2),'*','*'))<=2+pen17b[t,str(w)],
                                     name = CName)
NFL.update()
for t in team:
        Cname="17C_NO_CONSECUTIVEGAMES_%s"%(t)
        myConstrs[CName] = NFL.addConstr(quicksum(pen17a[t,str(w)]+pen17b[t,str(w)]for w in range(4,15)) <= 1,name = CName)
NFL.update()
        
#%%No team should play consecutive road games involving travel across more than 1 time zone 
westcoast=list(teamdata.loc[teamdata["TIMEZONE"]==4,"TEAM"])
eastcoast=list(teamdata.loc[teamdata["TIMEZONE"]==1,"TEAM"])
central=list(teamdata.loc[teamdata["TIMEZONE"]==2,"TEAM"])
mountain=list(teamdata.loc[teamdata["TIMEZONE"]==3,"TEAM"])
penalty18={}
for t in team:
    penalty18[t]=NFL.addVar(obj=-9, vtype=GRB.BINARY,name="PENALTY_FOR_RULE19")
NFL.update()
for w in range(1,18):
    for t in team:
        for a in away[t]:
            if a != "BYE":
                Cname="18_NO_TRAVELLING_TIMEZONES_THURSDAYNIGHT_%s"%(t)
                if a in westcoast:
                    myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(a,t,str(w),'*','*'))+
                                                     quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(eastcoast+central,t,str(w+1),'*','*'))<=0+penalty18[t],name = Cname)
                elif a in mountain:
                    myConstrs[Cname]=NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(a,t,str(w),'*','*'))+
                                                   quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(eastcoast,t,str(w+1),'*','*'))<=0+penalty18[t],name = Cname)
                elif t in central:
                    myConstrs[Cname]=NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(a,t,str(w),'*','*'))+
                                                   quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(westcoast,t,str(w+1),'*','*'))<=0+penalty18[t],name = Cname)
                else:
                    myConstrs[Cname]=NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(a,t,str(w),'*','*'))+
                                                   quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(westcoast+mountain,t,str(w+1),'*','*'))<=0+penalty18[t],name = Cname)
    
NFL.update()             
#%%c19No team playing a Thursday night road game should travel more than 1 time zone from home
penalty19={}
for t in team:
    penalty19[t]=NFL.addVar(obj=-9, vtype=GRB.BINARY,name="PENALTY_FOR_RULE19")
### 9 is subjective and depends on the best score
NFL.update()
for t in team:
    Cname="19_NO_TRAVELLING_TIMEZONES_THURSDAYNIGHT_%s"%(t)
    if t in westcoast:
        myConstrs[Cname] = NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(eastcoast+central,t,"*",'THUN','*'))<=0+penalty19[t],name = Cname)
    elif t in mountain:
         myConstrs[Cname]=NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(eastcoast,t,"*",'THUN','*')) <= 0+penalty19[t],name=Cname)

    elif t in central:
         myConstrs[Cname]=NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(westcoast,t,"*",'THUN','*')) <= 0+penalty19[t],name=Cname)
    else:
         myConstrs[Cname]=NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select(mountain+westcoast,t,"*",'THUN','*')) <= 0+penalty19[t],name=Cname)
    
NFL.update()        
#%%%NO TEAM SHOULD START WITH 2 AWAY GAMES
penalty20={}
for t in team:
    penalty20[t]=NFL.addVar(obj=-9, vtype=GRB.BINARY,name="PENALTY_FOR_RULE20")
### 9 is subjective and depends on the best score
NFL.update()

for t in team:
    Cname="20_NO_2AWAYGAMES_IN_1ST_WEEK_%s"%(t)
    myConstrs=NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select("*",t,"1",'*','*'))+
                            quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select("*",t,"2",'*','*')) <=1+penalty20[t],name=Cname)
NFL.update()

#%%%NO TEAM SHOULD END WITH 2 AWAY GAMES
penalty21={}
for t in team:
    penalty21[t]=NFL.addVar(obj=-9, vtype=GRB.BINARY,name="PENALTY_FOR_RULE21")
### 9 is subjective and depends on the best score
NFL.update()

for t in team:
    Cname="21_NO_2AWAYGAMES_IN_LAST_WEEK_%s"%(t)
    myConstrs=NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select("*",t,"15",'*','*'))+
                            quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select("*",t,"16",'*','*')) <=1+penalty21[t],name=Cname)
NFL.update()
#%%/Florida teams should not have an early home game in sept
FL=["JAC","MIA","TB"]
penalty22={}
for t in FL:
    penalty22[t]=NFL.addVar(obj=-7, vtype=GRB.BINARY,name="PENALTY_FOR_RULE21")
for t in FL:
     Cname="22_NO_SEPTGAME_IN_FLORIDA_%s"%(t)
     myConstrs=NFL.addConstr(quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select("*",t,"1",'*','*'))+
                             quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select("*",t,"2",'*','*'))+
                             quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select("*",t,"3",'*','*'))+
                             quicksum(Games[a,h,w,s,n] for a,h,w,s,n in gamelist.select("*",t,"4",'*','*')) <=0+penalty22[t],name=Cname)
NFL.update()
#%%
NFL.setParam('MIPFocus',1)
NFL.setParam('MIPGap',0.9)
NFL.optimize()
NFL.write('Test.lp')


              